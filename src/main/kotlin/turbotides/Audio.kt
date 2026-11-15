package turbotides

import com.badlogic.gdx.Gdx
import com.badlogic.gdx.audio.Sound
import com.badlogic.gdx.utils.Disposable

class Audio : Disposable {
    private val sounds = mutableMapOf<String, Sound>()
    private var engineId = -1L
    private var musicId = -1L
    private var wasMuted = false
    private var previousPhase = Phase.GARAGE
    private var previousMessageSequence = 0
    private var previousRace: Race? = null

    init {
        for (name in listOf("engine", "music", "go", "bonus", "bump", "finish")) {
            try {
                sounds[name] = Gdx.audio.newSound(Gdx.files.internal("audio/$name.wav"))
            } catch (exception: RuntimeException) {
                Gdx.app.error("Audio", "Sound unavailable: $name", exception)
            }
        }
    }

    private fun cue(name: String, muted: Boolean) {
        if (!muted) sounds[name]?.play(0.3f)
    }

    fun update(race: Race, muted: Boolean) {
        if (race !== previousRace) {
            // A retry replaces the race immediately, including its short cues.
            for (name in listOf("go", "bonus", "bump", "finish")) sounds[name]?.stop()
            previousRace = race
            previousPhase = Phase.GARAGE
            previousMessageSequence = 0
        }
        if ((muted && !wasMuted) || (race.phase == Phase.PAUSED && previousPhase != Phase.PAUSED)) {
            sounds.values.forEach { it.stop() }
            engineId = -1L
            musicId = -1L
        }
        // Resuming is not another start, and GO already has its own cue.
        if (race.phase == Phase.RACING && previousPhase == Phase.COUNTDOWN) cue("go", muted)
        if (race.phase == Phase.FINISHED && previousPhase != Phase.FINISHED) cue("finish", muted)
        if (race.messageSequence != previousMessageSequence) {
            previousMessageSequence = race.messageSequence
            if (race.messageTime > 0 && race.phase != Phase.PAUSED && race.message != "GO!") {
                cue(if (race.message.contains("bump") || race.message.contains("paint")) "bump" else "bonus", muted)
            }
        }
        previousPhase = race.phase
        wasMuted = muted
        val active = race.phase == Phase.RACING && !muted
        val engine = sounds["engine"]
        if (active) {
            if (engineId == -1L) engineId = engine?.loop(0.07f) ?: -1L
            engine?.setPitch(engineId, 0.65f + race.player.speed / 60f)
            engine?.setVolume(engineId, if (race.boosting) 0.14f else 0.085f)
        } else if (engineId != -1L) {
            engine?.stop(engineId)
            engineId = -1L
        }
        val music = sounds["music"]
        if (!muted && race.phase != Phase.PAUSED) {
            if (musicId == -1L) musicId = music?.loop(0.13f) ?: -1L
            music?.setVolume(musicId, if (race.phase == Phase.RACING) 0.1f else 0.18f)
        } else if (musicId != -1L) {
            music?.stop(musicId)
            musicId = -1L
        }
    }

    override fun dispose() {
        sounds.values.forEach { it.dispose() }
    }
}
