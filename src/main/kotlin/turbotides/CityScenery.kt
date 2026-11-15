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
        // A straight, level suspension span with International Orange, stepped
        // Art Deco portals, continuous cables and shore anchorages.
        val begin = track.bridgeStart
        val end = track.bridgeEnd
        for (distance in listOf(begin, end)) {
            val frame = track.frame(distance)
            val levels = listOf(-18f, 14f, 37f, 55f, 65f)
            for (side in listOf(-1f, 1f)) {
                for (level in 0 until levels.lastIndex) {
                    val bottom = levels[level]
                    val top = levels[level + 1]
                    g.box("c95237", frame.at(side * 15f, (top + bottom) / 2f), 3.6f - level * 0.35f, top - bottom, 4.2f, frame.heading)
                }
                g.box("bd4a32", frame.at(side * 15f, -15f), 7f, 7f, 9f, frame.heading)
            }
            for (height in listOf(14f, 37f, 55f, 65f)) {
                g.box("d95d3b", frame.at(0f, height), 33f, 2.1f, 3.5f, frame.heading)
                for (lane in -12..12 step 4) {
                    g.box("ec8457", frame.at(lane.toFloat(), height), 0.45f, 2.3f, 3.7f, frame.heading)
                }
            }
        }
        for (side in listOf(-1f, 1f)) {
            g.beam("d95d3b", track.frame(12f).at(side * 15f, 4f), track.frame(begin).at(side * 15f, 55f), 0.9f)
            g.beam("d95d3b", track.frame(end).at(side * 15f, 55f), track.frame(228f).at(side * 15f, 4f), 0.9f)
        }
        for (i in 0 until 36) {
            fun cable(fraction: Float, side: Float): Point3 {
                val height = 10f + 45f * (2f * fraction - 1f).pow(2)
                return track.frame(begin + (end - begin) * fraction).at(side * 15f, height)
            }
            val t = i / 36f
            for (side in listOf(-1f, 1f)) {
                val a = cable(t, side)
                g.beam("d95d3b", a, cable((i + 1) / 36f, side), 0.8f)
                g.beam("e88760", track.frame(begin + (end - begin) * t).at(side * 15f, 0.5f), a, 0.23f)
            }
        }
        for (i in 0..18) {
            val frame = track.frame(12f + i * 12f)
            g.box("aa4c36", frame.at(0f, -1.3f), 29f, 1.2f, 1.8f, frame.heading)
        }
        val houseColors = listOf("cfa38d", "abc6b7", "e6c981", "c4b2aa", "d2d7bd")
        for (i in 0 until 27) {
            val frame = track.frame(track.length * (0.31f + i * 0.021f))
            val p = frame.at(-25f, -4f)
            val height = 10f + i % 3 * 3f
            g.building(p, 10f, height, 12f, houseColors[i % houseColors.size], frame.heading)
            g.cone("78685b", p + Point3(0f, height + 2f, 0f), 15f, 4f, 16f, 4, frame.heading + 45f)
            val bay = p + frame.right * 5.8f
            g.box(houseColors[(i + 1) % houseColors.size], bay + Point3(0f, 5f, 0f), 2.5f, 8f, 5f, frame.heading)
            g.box("54777c", bay + frame.right * 1.3f + Point3(0f, 6f, 0f), 0.15f, 2.8f, 3.4f, frame.heading)
            g.box("f1dfbf", p + frame.right * 7.2f + Point3(0f, 0.8f, 0f), 3f, 1.6f, 6.5f, frame.heading)
        }
        // A tapered four-sided Pyramid, narrow service wings and a spire.
        val p = Point3(-42f, 12f, -35f)
        g.box("d5cbb6", p, 48f, 2f, 48f)
        for (x in listOf(-15f, 15f)) {
            for (z in listOf(-15f, 15f)) g.box("e9ddc3", p + Point3(x, 6f, z), 3f, 12f, 3f)
        }
        g.cone("eee0c8", p + Point3(0f, 56f, 0f), 44f, 88f, 44f)
        for (floor in 0..10) {
            val y = 17f + floor * 6.2f
            val width = 44f * (1f - (y - 12f) / 88f) * 0.7071f
            g.box("a9b6b2", p + Point3(0f, y, 0f), width + 0.3f, 0.65f, width + 0.3f)
        }
        for (side in listOf(-1f, 1f)) {
            g.box("e3d9c3", p + Point3(side * 12f, 50f, 0f), 4.5f, 56f, 5f)
        }
        g.beam("e6dbc4", p + Point3(0f, 100f, 0f), p + Point3(0f, 116f, 0f), 0.7f)
        // Bay traffic stays far below and outside the racing surface.
        for (i in 0..2) {
            val boat = Point3(255f + i * 45f, -3f, -45f + i * 50f)
            g.box("e4ded0", boat, 6f, 2f, 17f, 25f)
            g.box("658087", boat + Point3(0f, 2f, 0f), 4f, 2f, 8f, 25f)
        }
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
        val tiers = listOf(Triple(0f, 20f, 43f), Triple(20f, 66f, 30f), Triple(86f, 15f, 23f), Triple(101f, 13f, 16f))
        for ((base, height, width) in tiers) {
            g.building(tower + Point3(0f, base, 0f), width, height, width * 0.8f, "c7c1ad")
        }
        g.box("e4dbc0", tower + Point3(0f, 117f, 0f), 10f, 7f, 8f)
        g.cone("c9d4d1", tower + Point3(0f, 127f, 0f), 9f, 15f, 9f, 8)
        g.beam("e5ddc4", tower + Point3(0f, 133f, 0f), tower + Point3(0f, 153f, 0f), 0.8f)
        val crown = Point3(60f, 5f, -88f)
        g.building(crown, 25f, 62f, 25f, "b0ada0")
        for (i in 0..4) {
            g.cone("cbd6d4", crown + Point3(0f, 65f + i * 5f, 0f), 25f - i * 4f, 10f, 25f - i * 4f, 8)
        }
        g.beam("e0e8e1", crown + Point3(0f, 90f, 0f), crown + Point3(0f, 112f, 0f), 0.6f)
        for (x in listOf(80f, 110f)) {
            for (z in listOf(-70f, 12f, 80f)) g.building(Point3(x, 5f, z), 20f, 35f + abs(z) * 0.4f, 29f, "a89e8d")
        }
    }

    private fun chicago(g: Geometry) {
        val tower = Point3(-35f, 6f, -22f)
        val tubeHeights = listOf(60f, 80f, 106f, 80f, 128f, 128f, 60f, 106f, 106f)
        for (x in 0..2) {
            for (z in 0..2) {
                val height = tubeHeights[x * 3 + z]
                g.building(tower + Point3((x - 1) * 14f, 0f, (z - 1) * 14f), 13.8f, height, 13.8f, "354950")
            }
        }
        for (z in listOf(0f, 14f)) g.beam("e0e2cf", tower + Point3(0f, 128f, z), tower + Point3(0f, 158f, z), 1.1f)
        // Marina City's rounded towers contrast with the bundled-tube skyline.
        for (z in listOf(-10f, 32f)) {
            val center = Point3(62f, 4f, z)
            g.cylinder("6c7e7c", center + Point3(0f, 37f, 0f), 16f, 74f)
            for (floor in 0..16) {
                g.cylinder("d8cfb5", center + Point3(0f, 6f + floor * 4f, 0f), 23f, 1.3f)
            }
            g.cylinder("b6b7a3", center + Point3(0f, 75f, 0f), 20f, 2f)
        }
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
        for (i in 0..11) {
            val p = Point3(-230f - i % 3 * 40f, -3f, -170f + i / 3 * 100f)
            g.building(p, 25f, 25f + i % 5 * 9f, 33f, if (i % 2 == 0) "967d69" else "a7a99b")
        }
        // Lakefront park and short piers on the eastern shore.
        for (i in 0..13) {
            val frame = track.frame(track.length * (0.77f + i * 0.015f))
            g.tree(frame.at(-22f, -2f), 1.1f)
        }
        for (i in 0..4) g.box("c6b699", Point3(213f, -2.5f, -65f + i * 29f), 65f, 2f, 7f)
    }
}
