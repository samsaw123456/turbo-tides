package turbotides

import com.badlogic.gdx.backends.lwjgl3.Lwjgl3Application
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3ApplicationConfiguration
import com.badlogic.gdx.backends.lwjgl3.Lwjgl3WindowAdapter
import org.lwjgl.glfw.GLFW
import java.io.File

fun main(args: Array<String>) {
    // Retain X11/XWayland window controls and icons when that display is available.
    if (System.getProperty("os.name").startsWith("Linux") && !System.getenv("DISPLAY").isNullOrEmpty()) {
        GLFW.glfwInitHint(GLFW.GLFW_PLATFORM, GLFW.GLFW_PLATFORM_X11)
    }
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
