package turbotides

import com.badlogic.gdx.ApplicationAdapter
import com.badlogic.gdx.Gdx
import com.badlogic.gdx.Input
import com.badlogic.gdx.Preferences
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3Graphics
import org.lwjgl.glfw.GLFW
import java.io.File

class Game(private val telemetry: File? = null) : ApplicationAdapter() {
    var circuit = Circuit.SUNSET
        private set
    var paint = 0
        private set
    var difficulty = Difficulty.EASY
        private set
    var muted = false
        private set
    var reducedMotion = false
        private set
    var overview = true
        private set
    var newBest = false
        private set
    var saveError = false
        private set
    lateinit var race: Race
        private set
    private lateinit var world: World
    private val worlds = mutableMapOf<Circuit, World>()
    private lateinit var hud: Hud
    private lateinit var audio: Audio
    private lateinit var preferences: Preferences
    private var saved = false
    private var telemetryClock = 0f
    private var windowWidth = 1280
    private var windowHeight = 800
    private var windowX = 0
    private var windowY = 0
    private var restoreWindowUntil = 0L

    override fun create() {
        Gdx.app.log("Turbo Tides", "Renderer: ${Gdx.graphics.glVersion.rendererString}")
        preferences = Gdx.app.getPreferences(if (telemetry == null) "turbo-tides" else "turbo-tides-playtest")
        muted = preferences.getBoolean("muted", false)
        reducedMotion = preferences.getBoolean("reducedMotion", false)
        paint = preferences.getInteger("paint", 0).coerceIn(0, PAINTS.lastIndex)
        circuit = Circuit.entries.getOrElse(preferences.getInteger("circuit", 0)) { Circuit.SUNSET }
        difficulty = Difficulty.entries.getOrElse(preferences.getInteger("difficulty", 0)) { Difficulty.EASY }
        race = Race(Track(circuit), difficulty, paint)
        world = World(race.track)
        worlds[circuit] = world
        hud = Hud()
        audio = Audio()
    }

    fun changeCircuit(direction: Int) {
        selectCircuit(Circuit.entries[Math.floorMod(circuit.ordinal + direction, Circuit.entries.size)])
    }

    fun selectCircuit(selected: Circuit) {
        if (race.phase != Phase.GARAGE || selected == circuit) return
        circuit = selected
        overview = true
        world = worlds.getOrPut(circuit) { World(Track(circuit)) }
        race = Race(world.track, difficulty, paint)
        world.resetCamera()
        world.resize(Gdx.graphics.width, Gdx.graphics.height)
        saveSettings()
    }

    fun changePaint(direction: Int) {
        paint = (paint + direction + PAINTS.size) % PAINTS.size
        race = Race(race.track, difficulty, paint)
        overview = false
        saveSettings()
    }

    fun togglePreview() {
        overview = !overview
        world.resetCamera()
    }

    fun changeDifficulty(direction: Int) {
        if (race.phase != Phase.GARAGE) return
        difficulty = difficulty.next(direction)
        race = Race(race.track, difficulty, paint)
        saveSettings()
    }

    fun startRace() {
        race = Race(race.track, difficulty, paint)
        race.start()
        saved = false
        newBest = false
        world.resetCamera()
    }

    fun garage() {
        race = Race(race.track, difficulty, paint)
        world.resetCamera()
    }

    // Keep the old San Francisco record intact; the new bridge route has a
    // different length, so its times must not compete with the 1.1 layout.
    private val bestKey get() = "best-${circuit.name}-${difficulty.recordId}" + if (circuit == Circuit.SAN_FRANCISCO) "-v2" else ""

    fun bestTime(): Float? = preferences.getFloat(bestKey, -1f).takeIf { it > 0f && it.isFinite() }

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
        if (pressed(Input.Keys.F11)) toggleFullscreen()
        if (pressed(Input.Keys.ESCAPE)) {
            when (race.phase) {
                Phase.GARAGE -> Gdx.app.exit()
                Phase.PAUSED -> race.resume()
                Phase.FINISHED -> garage()
                else -> race.pause()
            }
        }
        if (pressed(Input.Keys.R) && race.phase != Phase.GARAGE) startRace()
        if (pressed(Input.Keys.P) && race.phase == Phase.GARAGE) togglePreview()
    }

    private fun toggleFullscreen() {
        val graphics = Gdx.graphics as Lwjgl3Graphics
        if (graphics.isFullscreen) {
            graphics.setWindowedMode(windowWidth, windowHeight)
            restoreWindowUntil = System.nanoTime() + 1_000_000_000L
        } else {
            // A rapid second toggle must not save an intermediate window-manager resize.
            if (restoreWindowUntil == 0L) {
                windowWidth = graphics.width
                windowHeight = graphics.height
                windowX = graphics.window.positionX
                windowY = graphics.window.positionY
            }
            restoreWindowUntil = 0L
            graphics.setFullscreenMode(graphics.displayMode)
        }
    }

    private fun restoreWindowBounds() {
        if (restoreWindowUntil == 0L) return
        if (System.nanoTime() >= restoreWindowUntil || Gdx.input.isButtonPressed(Input.Buttons.LEFT)) {
            restoreWindowUntil = 0L
            return
        }
        val graphics = Gdx.graphics as Lwjgl3Graphics
        // XWayland can apply decorations after the fullscreen transition and subtract
        // their height from the client area. Reconcile actual bounds briefly, without
        // assuming a border size or overriding subsequent mouse-driven window resizing.
        if (graphics.width != windowWidth || graphics.height != windowHeight) {
            GLFW.glfwSetWindowSize(graphics.window.windowHandle, windowWidth, windowHeight)
        }
        if (graphics.window.positionX != windowX || graphics.window.positionY != windowY) {
            graphics.window.setPosition(windowX, windowY)
        }
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
        restoreWindowBounds()
        race.advance(delta, controls())
        if (race.phase == Phase.FINISHED && !saved) {
            saved = true
            newBest = race.elapsed < (bestTime() ?: Float.MAX_VALUE)
            if (newBest) {
                preferences.putFloat(bestKey, race.elapsed)
                flushPreferences()
            }
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
            overview,
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
        val input = controls()
        val frame = race.track.frame(player.distance)
        val middle = world.camera.project(frame.at(0f).vector(), 0f, 0f, 1280f, 800f)
        val right = world.camera.project(frame.at(3f).vector(), 0f, 0f, 1280f, 800f)
        val opponents = race.rivals.joinToString(",") {
            """{"name":"${it.name}","distance":${it.distance},"speed":${it.speed},"finishTime":${it.finishTime}}"""
        }
        val contents = """{"phase":"${race.phase}","time":${race.elapsed},"countdown":${race.countdown},"distance":${player.distance},"lane":${player.lane},"speed":${player.speed},"lateralSpeed":${player.lateralSpeed},"curvature":${race.track.curvature(
            player.distance,
        )},"cornerForce":${race.cornerForce()},"screenRight":${right.x - middle.x},"cameraFov":${world.camera.fieldOfView},"inputSteer":${input.steer},"inputThrottle":${input.throttle},"inputBrake":${input.brake},"overview":$overview,"difficulty":"$difficulty","length":${race.track.length},"lap":${race.lap},"position":${race.position},"nitro":${race.nitro},"drifting":${race.drifting},"boosting":${race.boosting},"pads":${race.pads},"bumps":${race.bumps},"driftBonuses":${race.driftBonuses},"fps":${Gdx.graphics.framesPerSecond},"circuit":"$circuit","paint":$paint,"muted":$muted,"reducedMotion":$reducedMotion,"best":${bestTime()},"saveError":$saveError,"rivals":[$opponents]}"""
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
        worlds.values.forEach { it.dispose() }
    }
}
