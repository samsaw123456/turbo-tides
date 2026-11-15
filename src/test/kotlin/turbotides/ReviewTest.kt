package turbotides

import kotlin.math.*
import kotlin.test.*

class ReviewTest {
    private fun race(): Race = Race(Track(Circuit.SUNSET)).also {
        it.start()
        repeat(420) { _ -> it.advance(Race.STEP, Controls()) }
        it.rivals.forEach { rival -> rival.finishTime = 1f }
    }

    @Test fun `visible car lengths cannot pass through each other during cooldown`() {
        val race = race()
        val rival = race.rivals.first()
        rival.finishTime = null
        race.player.distance = 100f
        race.player.lane = 0f
        rival.distance = 104f
        rival.lane = 0f
        repeat(15) {
            race.player.speed = 62f
            rival.speed = 0f
            race.advance(Race.STEP, Controls(throttle = true))
            // Chassis meshes are 4.2m long, independent of contact constants.
            val distance = abs(race.track.relativeDistance(race.player.distance, rival.distance))
            assertTrue(distance >= 4.19f, "Visible chassis overlap: $distance")
        }
        assertEquals(1, race.bumps, "The cooldown limits feedback, not physical separation")
    }

    @Test fun `visible wheels cannot overlap laterally`() {
        val race = race()
        val rival = race.rivals.first()
        rival.finishTime = null
        race.player.distance = 100f
        rival.distance = 100f
        race.player.lane = -1.15f
        rival.lane = 1.15f
        race.advance(Race.STEP, Controls())
        // Outer wheel meshes extend to approximately +/-1.3m.
        assertTrue(abs(race.player.lane - rival.lane) >= 2.59f)
    }

    @Test fun `rivals also make solid contact and recover to overtake a parked player`() {
        val contact = race()
        val a = contact.rivals[0]
        val b = contact.rivals[1]
        a.finishTime = null
        b.finishTime = null
        a.distance = 100f
        b.distance = 104f
        a.lane = 0f
        b.lane = 0f
        contact.advance(Race.STEP, Controls())
        assertTrue(abs(contact.track.relativeDistance(a.distance, b.distance)) >= 4.19f)
        assertEquals(0, contact.bumps, "AI-only contact must not penalize the player")
        for (circuit in Circuit.entries) {
            for (difficulty in Difficulty.entries) {
                val race = Race(Track(circuit), difficulty)
                race.start()
                repeat(150 * 120) { race.advance(Race.STEP, Controls()) }
                assertTrue(race.rivals.all { it.finishTime != null }, "$circuit $difficulty has a stranded rival")
                assertEquals(0f, race.player.distance, "Rivals must pass without moving the parked player")
            }
        }
    }

    @Test fun `physics and contacts agree at ten and 240 frames per second`() {
        fun drive(hz: Int): Race = Race(Track(Circuit.CHICAGO)).also { race ->
            race.start()
            repeat(hz * 30) { race.advance(1f / hz, Controls(throttle = true, boost = true)) }
        }
        val slow = drive(10)
        val fast = drive(240)
        assertEquals(slow.player.distance, fast.player.distance, 0.75f)
        assertEquals(slow.player.lane, fast.player.lane, 0.1f)
        assertEquals(slow.bumps, fast.bumps)
        assertEquals(slow.elapsed, fast.elapsed, 0.02f)
    }

    @Test fun `the complete angled car stays inside the visible barrier`() {
        for (direction in listOf(-1f, 1f)) {
            val race = race()
            race.player.speed = 60f
            repeat(480) {
                race.advance(Race.STEP, Controls(throttle = true, steer = direction, drift = true))
                val yaw = abs(race.player.lateralSpeed * if (race.drifting) 2.7f else 0.7f) * PI.toFloat() / 180f
                val wheelExtent = 1.3f * abs(cos(yaw)) + 2.1f * abs(sin(yaw))
                // The wall center is 13.4m out and its thickness is 0.55m.
                assertTrue(abs(race.player.lane) + wheelExtent <= 13.1251f, "Angled car protrudes through barrier")
            }
        }
    }
}
