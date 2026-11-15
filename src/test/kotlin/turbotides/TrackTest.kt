package turbotides

import kotlin.math.abs
import kotlin.test.*

class TrackTest {
    @Test fun `positive lane appears to the right in the chase camera`() {
        com.badlogic.gdx.utils.GdxNativesLoader.load()
        val camera = com.badlogic.gdx.graphics.PerspectiveCamera(67f, 1280f, 800f)
        for (circuit in Circuit.entries) {
            val track = Track(circuit)
            repeat(24) { index ->
                val frame = track.frame(track.length * index / 24f)
                val eye = frame.center - frame.forward * 12f + Point3(0f, 6f, 0f)
                camera.position.set(eye.x, eye.y, eye.z)
                camera.up.set(0f, 1f, 0f)
                camera.lookAt(frame.center.x, frame.center.y, frame.center.z)
                camera.update()
                fun screenX(lane: Float): Float {
                    val point = frame.at(lane)
                    return camera.project(com.badlogic.gdx.math.Vector3(point.x, point.y, point.z), 0f, 0f, 1280f, 800f).x
                }
                assertTrue(screenX(3f) > screenX(0f), "$circuit positive steering must appear right at sample $index")
                assertTrue(screenX(-3f) < screenX(0f), "$circuit negative steering must appear left at sample $index")
            }
        }
    }

    @Test fun `circuit joins without position height or direction jumps`() {
        for (circuit in Circuit.entries) {
            val track = Track(circuit)
            assertTrue(track.length > 800 && track.length < 1600)
            assertTrue((track.frame(-0.01f).center - track.frame(0.01f).center).length() < 0.03f)
            assertTrue((track.frame(0f).forward - track.frame(track.length).forward).length() < 0.001f)
            repeat(1000) { i ->
                val distance = i / 1000f * track.length
                assertTrue((track.frame(distance + 1f).center - track.frame(distance).center).length() in 0.98f..1.02f)
                assertTrue(abs(track.curvature(distance)) < 0.1f)
            }
        }
    }

    @Test fun `wrap and short relative distance work across seam`() {
        val track = Track(Circuit.SUNSET)
        assertEquals(track.length - 3f, track.wrap(-3f), 0.001f)
        assertEquals(5f, track.wrap(track.length * 2 + 5), 0.001f)
        assertEquals(4f, track.relativeDistance(2f, track.length - 2f), 0.001f)
    }

    @Test fun `road edges are consistently spaced from the center`() {
        val track = Track(Circuit.CINDER)
        for (i in 0..100) {
            val frame = track.frame(i * 10f)
            assertEquals(18f, (frame.at(-9f) - frame.at(9f)).length(), 0.001f)
        }
    }

    @Test fun `city circuits have usable grades distinct routes and no overlapping road sections`() {
        val tracks = Circuit.entries.map(::Track)
        assertEquals(tracks.size, tracks.map { it.length.toInt() }.toSet().size)
        assertTrue(Track(Circuit.SAN_FRANCISCO).elevation > 29f)
        assertTrue(Track(Circuit.NEW_YORK).elevation < 3f)
        for (track in tracks) {
            val samples = (0 until 160).map { track.frame(it * track.length / 160) }
            val maxGrade = if (track.circuit == Circuit.CINDER) 0.35f else 0.23f
            samples.forEach { assertTrue(abs(it.forward.y) < maxGrade, track.circuit.title) }
            for (a in samples.indices) {
                for (b in a + 1 until samples.size) {
                    val apart = kotlin.math.min(b - a, samples.size - (b - a)) * track.length / samples.size
                    if (apart > 50f) assertTrue((samples[a].center - samples[b].center).length() > 30f, track.circuit.title)
                }
            }
        }
    }
}
