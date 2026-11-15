package turbotides

import com.badlogic.gdx.Files
import com.badlogic.gdx.Gdx
import com.badlogic.gdx.audio.Sound
import com.badlogic.gdx.files.FileHandle
import java.lang.reflect.Proxy
import kotlin.test.*

class AudioTest {
    private class Output {
        val plays = mutableListOf<String>()
        val stops = mutableListOf<String>()
    }

    // Exercise the real audio coordinator against a recording device boundary.
    // Native PCM playtests separately verify that these calls reach the device.
    private fun withOutput(test: (Audio, Output) -> Unit) {
        val oldAudio = Gdx.audio
        val oldFiles = Gdx.files
        val output = Output()
        Gdx.files = Proxy.newProxyInstance(Files::class.java.classLoader, arrayOf(Files::class.java)) { _, method, args ->
            if (method.name == "internal") FileHandle(args!![0] as String) else null
        } as Files
        Gdx.audio =
            Proxy.newProxyInstance(com.badlogic.gdx.Audio::class.java.classLoader, arrayOf(com.badlogic.gdx.Audio::class.java)) {
                    _,
                    method,
                    args,
                ->
                if (method.name != "newSound") return@newProxyInstance null
                val name = (args!![0] as FileHandle).nameWithoutExtension()
                Proxy.newProxyInstance(Sound::class.java.classLoader, arrayOf(Sound::class.java)) { _, call, _ ->
                    when (call.name) {
                        "play" -> {
                            output.plays.add(name)
                            1L
                        }
                        "loop" -> 1L
                        "stop" -> {
                            output.stops.add(name)
                            null
                        }
                        else -> null
                    }
                } as Sound
            } as com.badlogic.gdx.Audio
        try {
            val audio = Audio()
            try {
                test(audio, output)
            } finally {
                audio.dispose()
            }
        } finally {
            Gdx.audio = oldAudio
            Gdx.files = oldFiles
        }
    }

    private fun launch(audio: Audio): Race {
        val race = Race(Track(Circuit.SUNSET))
        race.start()
        audio.update(race, false)
        repeat(420) {
            race.advance(Race.STEP, Controls())
            audio.update(race, false)
        }
        assertEquals(Phase.RACING, race.phase)
        return race
    }

    @Test fun `starting a race plays one go cue and no bonus cue`() = withOutput { audio, output ->
        launch(audio)
        assertEquals(listOf("go"), output.plays)
    }

    @Test fun `pause stops transient output and resume does not replay go`() = withOutput { audio, output ->
        val race = launch(audio)
        output.plays.clear()
        output.stops.clear()
        race.pause()
        audio.update(race, false)
        assertTrue("go" in output.stops, "A playing countdown cue must be stopped by pause")
        race.resume()
        audio.update(race, false)
        assertTrue(output.plays.isEmpty(), "Resume must not replay a start or bonus cue")
    }

    @Test fun `two turbo pad events each produce feedback but mute discards old cues`() = withOutput { audio, output ->
        val race = launch(audio)
        race.rivals.forEach { it.finishTime = 1f }
        output.plays.clear()
        fun pad(index: Int, muted: Boolean) {
            race.player.distance = race.track.padDistance(index)
            race.player.lane = race.track.padLane(index)
            race.player.speed = 5f
            race.advance(Race.STEP, Controls())
            audio.update(race, muted)
        }
        pad(0, false)
        pad(1, false)
        assertEquals(listOf("bonus", "bonus"), output.plays)
        pad(2, true)
        audio.update(race, false)
        assertEquals(listOf("bonus", "bonus"), output.plays, "Unmute must not replay muted events")
    }

    @Test fun `each fresh countdown plays a new go cue`() = withOutput { audio, output ->
        launch(audio)
        output.stops.clear()
        launch(audio)
        assertEquals(listOf("go", "go"), output.plays)
        assertTrue("go" in output.stops, "Restart must clear the previous race's transient cues")
    }
}
