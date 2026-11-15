package turbotides

import com.badlogic.gdx.graphics.g3d.utils.MeshPartBuilder
import kotlin.math.*

/** Recognisable silhouettes, with all solid scenery outside the racing corridor. */
class CityScenery(private val track: Track) {
    fun build(part: MeshPartBuilder) {
        val g = Geometry(part)
        when (track.circuit) {
            Circuit.SAN_FRANCISCO -> sanFrancisco(g)
            Circuit.SILICON_VALLEY -> siliconValley(g)
            Circuit.NEW_YORK -> newYork(g)
            Circuit.CHICAGO -> chicago(g)
            else -> return
        }
        for (i in 0 until 42) {
            val frame = track.frame((i + 0.5f) / 42f * track.length)
            val p = frame.at(17f, -1f)
            // Trackside lamps remain beyond the barrier and below the skyline.
            g.box("40565c", p + Point3(0f, 4f, 0f), 0.3f, 8f, 0.3f)
            g.box("f7e4bb", p + Point3(0f, 8f, 0f), 2.2f, 0.35f, 1f, frame.heading)
        }
    }

    private fun sanFrancisco(g: Geometry) {
        // A curved suspension span follows the exact driven surface. Tower
        // legs are outside the walls; even the lowest cable clears the cars.
        val begin = track.length * 0.015f
        val end = track.length * 0.205f
        for (distance in listOf(begin, end)) {
            val frame = track.frame(distance)
            for (side in listOf(-1f, 1f)) {
                val p = frame.at(side * 15f, 13f)
                g.box("c95237", p, 3f, 74f, 4f, frame.heading)
            }
            for (height in listOf(14f, 37f, 48f)) {
                g.box("de6240", frame.at(0f, height), 33f, 2.3f, 3f, frame.heading)
            }
        }
        for (i in 0 until 36) {
            val t = i / 36f
            val next = (i + 1) / 36f
            fun cable(fraction: Float, side: Float): Point3 {
                val height = 10f + 38f * (2f * fraction - 1f).pow(2)
                return track.frame(begin + (end - begin) * fraction).at(side * 15f, height)
            }
            for (side in listOf(-1f, 1f)) {
                val a = cable(t, side)
                g.beam("d95d3b", a, cable(next, side), 0.9f)
                g.beam("e88760", track.frame(begin + (end - begin) * t).at(side * 15f, 1f), a, 0.25f)
            }
        }
        val houseColors = listOf("cfa38d", "abc6b7", "e6c981", "c4b2aa", "d2d7bd")
        for (i in 0 until 27) {
            val frame = track.frame(track.length * (0.31f + i * 0.021f))
            val p = frame.at(-25f, -4f)
            val height = 10f + i % 3 * 3f
            g.building(p, 10f, height, 12f, houseColors[i % houseColors.size], frame.heading)
            g.cone("78685b", p + Point3(0f, height + 2f, 0f), 15f, 4f, 16f, 4, frame.heading + 45f)
        }
        // A pointed downtown landmark, grounded on its own visible plaza.
        val p = Point3(-48f, 8f, -35f)
        g.building(p, 27f, 13f, 27f, "ded5bf", windows = false)
        g.cone("eee0c8", p + Point3(0f, 56f, 0f), 40f, 86f, 40f)
        g.beam("e6dbc4", p + Point3(0f, 99f, 0f), p + Point3(0f, 112f, 0f), 0.8f)
        for (i in 0..14) {
            val angle = i * 2.4f
            val tree = Point3(cos(angle) * 87f, 8f, sin(angle) * 65f)
            g.tree(tree, 1.3f)
        }
    }

    private fun siliconValley(g: Geometry) {
        // The low circular campus is built from tangent sections, not a decal.
        val center = Point3(-18f, 5f, 0f)
        for (i in 0 until 32) {
            val angle = i * 2f * PI.toFloat() / 32
            val p = center + Point3(cos(angle) * 64f, 0f, sin(angle) * 64f)
            val yaw = -angle * 180f / PI.toFloat()
            g.building(p, 15f, 11f, 14f, "cdd6c5", yaw, windows = false)
            g.box("537f89", p + Point3(0f, 7f, 0f), 15.2f, 5f, 14.2f, yaw)
            g.box("294c62", p + Point3(0f, 11.7f, 0f), 12f, 0.35f, 11f, yaw)
        }
        for (i in 0..20) {
            val angle = i * 2.4f
            g.tree(center + Point3(cos(angle) * (20f + i % 3 * 9f), 0f, sin(angle) * (20f + i % 3 * 9f)), 0.9f)
        }
        for (i in 0..13) {
            val frame = track.frame((i + 0.2f) / 14f * track.length)
            val p = frame.at(-39f, -5f)
            g.building(p, 30f, 10f + i % 3 * 3f, 18f, if (i % 2 == 0) "d7c9ac" else "a7b8ac", frame.heading)
            g.box("305b71", p + Point3(0f, 11f + i % 3 * 3f, 0f), 25f, 0.6f, 12f, frame.heading)
            g.tree(frame.at(-21f, -1f), 1.2f)
        }
        // Communications dish and its support; no branded company logos.
        val dish = Point3(117f, 4f, -42f)
        g.box("d3cbb3", dish + Point3(0f, 8f, 0f), 2f, 16f, 2f)
        g.cone("f1e7ce", dish + Point3(0f, 18f, 0f), 21f, 7f, 21f, 12)
        g.beam("536e74", dish + Point3(0f, 21f, 0f), dish + Point3(4f, 28f, 0f), 0.5f)
        for (i in 0..7) {
            g.cone("8ca775", Point3(-320f + i * 85f, 6f, -310f), 110f, 70f + i % 3 * 24f, 100f, 6)
        }
    }

    private fun newYork(g: Geometry) {
        g.box("6f9464", Point3(0f, 5f, 32f), 115f, 2f, 115f)
        g.box("c2b796", Point3(0f, 6.1f, 32f), 6f, 0.15f, 115f)
        g.box("c2b796", Point3(0f, 6.2f, 32f), 115f, 0.15f, 6f)
        for (i in 0..23) {
            g.tree(Point3(-45f + i % 6 * 18f, 6f, -9f + i / 6 * 27f), 1.3f)
        }
        for (i in 0 until 22) {
            val frame = track.frame((i + 0.5f) / 22f * track.length)
            val p = frame.at(-35f, -3f)
            g.building(p, 22f, 30f + (i * 17 % 55), 24f, listOf("839b9d", "ac9c86", "8f9698", "bdad91")[i % 4], frame.heading)
            if (i % 3 == 0) {
                val taxi = frame.at(-17.5f, 0.5f)
                g.box("efbe3c", taxi, 2.2f, 1.2f, 4.6f, frame.heading)
                g.box("32515b", taxi + Point3(0f, 1f, 0f), 1.8f, 0.8f, 2.2f, frame.heading)
            }
        }
        val tower = Point3(-55f, 5f, -88f)
        for (i in 0..3) {
            g.building(tower + Point3(0f, i * 27f, 0f), 34f - i * 6f, 27f, 30f - i * 5f, "b9b9a7")
        }
        g.cone("d7d8bd", tower + Point3(0f, 118f, 0f), 15f, 20f, 15f)
        g.beam("e5ddc4", tower + Point3(0f, 125f, 0f), tower + Point3(0f, 147f, 0f), 1f)
        for (x in listOf(80f, 110f)) {
            for (z in listOf(-70f, 12f, 80f)) g.building(Point3(x, 5f, z), 20f, 35f + abs(z) * 0.4f, 29f, "a89e8d")
        }
    }

    private fun chicago(g: Geometry) {
        val tower = Point3(-35f, 6f, -22f)
        for (x in -1..1) {
            for (z in -1..1) {
                val height = 74f + (3 - abs(x) - abs(z)) * 18f
                g.building(tower + Point3(x * 14f, 0f, z * 14f), 13.8f, height, 13.8f, "4b626b")
            }
        }
        for (x in listOf(-7f, 7f)) g.beam("e0e2cf", tower + Point3(x, 120f, 0f), tower + Point3(x, 150f, 0f), 1.1f)
        for (i in 0..12) {
            val frame = track.frame(track.length * (0.3f + i * 0.042f))
            g.building(frame.at(-34f, -4f), 23f, 18f + i % 4 * 12f, 25f, if (i % 2 == 0) "ac7b60" else "c7b99c", frame.heading)
        }
        // An elevated train crosses the course with 10m of road clearance.
        val crossing = track.frame(track.length * 0.27f)
        val yaw = crossing.heading + 90f
        g.box("5c6e6d", crossing.at(0f, 12f), 7f, 1.8f, 146f, yaw)
        for (lane in listOf(-64f, -30f, 30f, 64f)) {
            g.box("6a7b77", crossing.at(lane, 4f), 2.4f, 16f, 2.4f)
        }
        for (i in -2..2) {
            val p = crossing.at(i * 12f, 15f)
            g.box("ddd7bb", p, 5.1f, 4f, 10.8f, yaw)
            g.box("4a6970", p + Point3(0f, 0.4f, 0f), 5.15f, 1.5f, 9f, yaw)
            g.box("ba6749", p + Point3(0f, -1.1f, 0f), 5.2f, 0.5f, 10f, yaw)
        }
        // Lakefront park and short piers on the eastern shore.
        for (i in 0..13) {
            val frame = track.frame(track.length * (0.77f + i * 0.015f))
            g.tree(frame.at(-22f, -2f), 1.1f)
        }
        for (i in 0..4) g.box("c6b699", Point3(213f, -2.5f, -65f + i * 29f), 65f, 2f, 7f)
    }
}
