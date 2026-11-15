package turbotides

import com.badlogic.gdx.ApplicationAdapter
import com.badlogic.gdx.Gdx
import com.badlogic.gdx.Input
import com.badlogic.gdx.Preferences
import java.io.File

class Game(private val telemetry: File? = null) : ApplicationAdapter() {
    var circuit = Circuit.SUNSET
        private set
    var paint = 0
        private set
    var difficulty = Difficulty.CRUISE
        private set
    var muted = false
        private set
    var reducedMotion = false
        private set
    var newBest = false
        private set
    var saveError = false
        private set
    lateinit var race: Race
        private set
    private lateinit var world: World
    private lateinit var hud: Hud
    private lateinit var audio: Audio
    private lateinit var preferences: Preferences
    private var saved = false
    private var telemetryClock = 0f
    private var previousPhase = Phase.GARAGE
    private var previousMessage = ""
    private var windowWidth = 1280
    private var windowHeight = 800

    override fun create() {
        Gdx.app.log("Turbo Tides", "Renderer: ${Gdx.graphics.glVersion.rendererString}")
        preferences = Gdx.app.getPreferences(if (telemetry == null) "turbo-tides" else "turbo-tides-playtest")
        muted = preferences.getBoolean("muted", false)
        reducedMotion = preferences.getBoolean("reducedMotion", false)
        paint = preferences.getInteger("paint", 0).coerceIn(0, PAINTS.lastIndex)
        circuit = Circuit.entries.getOrElse(preferences.getInteger("circuit", 0)) { Circuit.SUNSET }
        difficulty = Difficulty.entries.getOrElse(preferences.getInteger("difficulty", 0)) { Difficulty.CRUISE }
        race = Race(Track(circuit), difficulty, paint)
        world = World(race.track)
        hud = Hud()
        audio = Audio()
    }

    fun changeCircuit(direction: Int) {
        circuit = Circuit.entries[(circuit.ordinal + direction + Circuit.entries.size) % Circuit.entries.size]
        world.dispose()
        race = Race(Track(circuit), difficulty, paint)
        world = World(race.track)
        world.resize(Gdx.graphics.width, Gdx.graphics.height)
        saveSettings()
    }

    fun changePaint(direction: Int) {
        paint = (paint + direction + PAINTS.size) % PAINTS.size
        race = Race(race.track, difficulty, paint)
        saveSettings()
    }

    fun changeDifficulty() {
        difficulty = if (difficulty == Difficulty.CRUISE) Difficulty.RACE else Difficulty.CRUISE
        race = Race(race.track, difficulty, paint)
        saveSettings()
    }

    fun startRace() {
        race = Race(race.track, difficulty, paint)
        race.start()
        saved = false
        newBest = false
        previousMessage = ""
        world.resetCamera()
    }

    fun garage() {
        race = Race(race.track, difficulty, paint)
        world.resetCamera()
    }

    fun bestTime(): Float? = preferences.getFloat("best-${circuit.name}-${difficulty.name}", -1f).takeIf { it > 0f && it.isFinite() }

    private fun saveSettings() {
        preferences.putBoolean("muted", muted).putBoolean("reducedMotion", reducedMotion)
            .putInteger("paint", paint).putInteger("circuit", circuit.ordinal).putInteger("difficulty", difficulty.ordinal)
        flushPreferences()
    }

    private fun flushPreferences() {
        try {
            preferences.flush()
            saveError = false
        } catch (exception: RuntimeException) {
            saveError = true
            Gdx.app.error("Save", "Could not save game settings and records", exception)
        }
    }

    private fun keys() {
        fun pressed(key: Int) = Gdx.input.isKeyJustPressed(key)
        if (pressed(Input.Keys.M)) {
            muted = !muted
            saveSettings()
        }
        if (pressed(Input.Keys.N)) {
            reducedMotion = !reducedMotion
            saveSettings()
        }
        if (pressed(Input.Keys.F11)) {
            if (Gdx.graphics.isFullscreen) {
                Gdx.graphics.setWindowedMode(windowWidth, windowHeight)
            } else {
                windowWidth = Gdx.graphics.width
                windowHeight = Gdx.graphics.height
                Gdx.graphics.setFullscreenMode(Gdx.graphics.displayMode)
            }
        }
        if (pressed(Input.Keys.ESCAPE)) {
            when (race.phase) {
                Phase.GARAGE -> Gdx.app.exit()
                Phase.PAUSED -> race.resume()
                Phase.FINISHED -> garage()
                else -> race.pause()
            }
        }
        if (pressed(Input.Keys.R) && race.phase != Phase.GARAGE) startRace()
    }

    private fun controls(): Controls {
        fun down(vararg keys: Int) = keys.any { Gdx.input.isKeyPressed(it) }
        return Controls(
            throttle = down(Input.Keys.W, Input.Keys.UP),
            brake = down(Input.Keys.S, Input.Keys.DOWN),
            steer = (if (down(Input.Keys.D, Input.Keys.RIGHT)) 1f else 0f) - (if (down(Input.Keys.A, Input.Keys.LEFT)) 1f else 0f),
            drift = down(Input.Keys.SPACE),
            boost = down(Input.Keys.SHIFT_LEFT, Input.Keys.SHIFT_RIGHT),
        )
    }

    override fun render() {
        val delta = Gdx.graphics.deltaTime.coerceAtMost(0.1f)
        keys()
        race.advance(delta, controls())
        if (race.phase == Phase.FINISHED && !saved) {
            saved = true
            newBest = race.elapsed < (bestTime() ?: Float.MAX_VALUE)
            if (newBest) {
                preferences.putFloat("best-${circuit.name}-${difficulty.name}", race.elapsed)
                flushPreferences()
            }
        }
        if (race.phase != previousPhase) {
            if (race.phase == Phase.RACING) audio.cue("go", muted)
            if (race.phase == Phase.FINISHED) audio.cue("finish", muted)
            previousPhase = race.phase
        }
        if (race.messageTime > 0 && race.message != previousMessage) {
            previousMessage = race.message
            audio.cue(if (race.message.contains("bump") || race.message.contains("paint")) "bump" else "bonus", muted)
        }
        audio.update(race, muted)
        world.render(
            race,
            if (race.phase ==
                Phase.PAUSED
            ) {
                0f
            } else {
                delta
            },
            reducedMotion,
            Gdx.input.isKeyPressed(Input.Keys.C) && race.phase == Phase.RACING,
        )
        hud.draw(this)
        if (telemetry != null) {
            telemetryClock += delta
            if (telemetryClock > 0.08f) {
                telemetryClock = 0f
                writeTelemetry()
            }
        }
    }

    private fun writeTelemetry() {
        val player = race.player
        val contents = """{"phase":"${race.phase}","time":${race.elapsed},"countdown":${race.countdown},"distance":${player.distance},"lane":${player.lane},"speed":${player.speed},"lateralSpeed":${player.lateralSpeed},"curvature":${race.track.curvature(
            player.distance,
        )},"length":${race.track.length},"lap":${race.lap},"position":${race.position},"nitro":${race.nitro},"drifting":${race.drifting},"boosting":${race.boosting},"pads":${race.pads},"bumps":${race.bumps},"driftBonuses":${race.driftBonuses},"fps":${Gdx.graphics.framesPerSecond},"circuit":"$circuit","paint":$paint,"muted":$muted,"reducedMotion":$reducedMotion,"best":${bestTime()},"saveError":$saveError}"""
        try {
            telemetry?.writeText(contents)
        } catch (exception: Exception) {
            Gdx.app.error("Telemetry", "Cannot write diagnostic file", exception)
        }
    }

    fun focusLost() {
        if (::race.isInitialized) race.pause()
    }

    override fun resize(width: Int, height: Int) {
        world.resize(width, height)
        hud.resize(width, height)
    }

    override fun dispose() {
        audio.dispose()
        hud.dispose()
        world.dispose()
    }
}
