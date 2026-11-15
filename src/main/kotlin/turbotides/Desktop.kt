package turbotides

import com.badlogic.gdx.backends.lwjgl3.Lwjgl3Application
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3ApplicationConfiguration
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3WindowAdapter
import java.io.File

fun main(args: Array<String>) {
    val telemetryIndex = args.indexOf("--telemetry")
    val telemetry = if (telemetryIndex >= 0) args.getOrNull(telemetryIndex + 1)?.let(::File) else null
    val game = Game(telemetry)
    val config = Lwjgl3ApplicationConfiguration().apply {
        setTitle("Turbo Tides")
        setWindowedMode(1280, 800)
        setWindowSizeLimits(960, 640, -1, -1)
        setWindowIcon("art/icon-128.png", "art/icon-64.png", "art/icon-32.png")
        setForegroundFPS(120)
        setBackBufferConfig(8, 8, 8, 8, 24, 0, 4)
        setIdleFPS(30)
        // Keep input/rendering responsive when desktop buffer synchronization
        // stalls; the foreground FPS cap above still bounds rendering work.
        useVsync(false)
        setAudioConfig(32, 512, 9)
        setWindowListener(object : Lwjgl3WindowAdapter() {
            override fun focusLost() {
                game.focusLost()
            }
        })
    }
    Lwjgl3Application(game, config)
}
