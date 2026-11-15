package turbotides

import kotlin.math.*
import kotlin.test.*

class DifficultyTest {
    @Test fun `four settings wrap in both directions and preserve old record identities`() {
        assertEquals(listOf("Easy", "Medium", "Hard", "Super Hard"), Difficulty.entries.map { it.title })
        assertEquals(Difficulty.SUPER_HARD, Difficulty.EASY.next(-1))
        assertEquals(Difficulty.EASY, Difficulty.SUPER_HARD.next(1))
        for (level in Difficulty.entries) assertEquals(level, level.next(1).next(-1))
        assertEquals("CRUISE", Difficulty.entries[0].recordId)
        assertEquals("RACE", Difficulty.entries[1].recordId)
        assertEquals(4, Difficulty.entries.map { it.recordId }.toSet().size)
    }

    @Test fun `every harder setting makes the entire rival field finish faster on every circuit`() {
        for (circuit in Circuit.entries) {
            var previous: List<Float>? = null
            for (level in Difficulty.entries) {
                val race = Race(Track(circuit), level)
                race.start()
                repeat(120 * 120) {
                    race.advance(Race.STEP, Controls())
                    assertTrue(race.rivals.all { it.speed in 0f..87.001f })
                }
                val times = race.rivals.map { assertNotNull(it.finishTime, "$circuit $level stranded ${it.name}") }.sorted()
                previous?.zip(times)?.forEach { (easier, harder) ->
                    assertTrue(harder < easier * 0.95f, "$circuit $level did not improve by at least 5%: $easier -> $harder")
                }
                previous = times
                println("$circuit $level winner=${times.first()} field=${times.last()}")
            }
        }
    }

    private fun drive(circuit: Circuit, level: Difficulty, pads: Boolean, drift: Boolean, boost: Boolean): Race {
        val race = Race(Track(circuit), level)
        race.start()
        var input = Controls()
        repeat(120 * 120) { frame ->
            // Digital steering refreshed at 20Hz; never move cars or alter fuel.
            if (frame % 6 == 0) {
                val time = race.elapsed
                var target = if (drift) if ((time / 0.9f).toInt() % 2 == 0) 4.5f else -4.5f else 0f
                if (pads) {
                    for (pad in 0..2) {
                        val ahead = race.track.wrap(race.track.padDistance(pad) - race.player.distance)
                        if (ahead < 65f || ahead > race.track.length - 4f) target = race.track.padLane(pad)
                    }
                }
                val slide = drift && time % 0.9f < 0.75f
                val correction = (target - race.player.lane) * 3.5f - race.player.lateralSpeed * 0.9f - race.cornerForce()
                val steering = if (abs(correction) < 1.32f) 0f else sign(correction)
                input = Controls(throttle = true, steer = steering, drift = slide, boost = boost)
            }
            race.advance(Race.STEP, input)
            if (race.phase == Phase.FINISHED) return race
        }
        fail("$circuit $level did not finish")
    }

    @Test fun `easy allows a clean win without boost while medium rewards pads`() {
        for (circuit in Circuit.entries) {
            assertEquals(1, drive(circuit, Difficulty.EASY, pads = false, drift = false, boost = false).position, "$circuit Easy")
            assertEquals(1, drive(circuit, Difficulty.MEDIUM, pads = true, drift = false, boost = true).position, "$circuit Medium")
        }
    }

    @Test fun `hard and super hard punish skipping drifts but remain beatable with digital controls`() {
        for (circuit in Circuit.entries) {
            for (level in listOf(Difficulty.HARD, Difficulty.SUPER_HARD)) {
                val ordinary = drive(circuit, level, pads = true, drift = false, boost = true)
                val skilled = drive(circuit, level, pads = true, drift = true, boost = true)
                println("$circuit $level ordinary=${ordinary.position}/${ordinary.elapsed} skilled=${skilled.position}/${skilled.elapsed}")
                assertTrue(ordinary.position > 1, "$circuit $level should demand more than pads and held boost")
                assertEquals(1, skilled.position, "$circuit $level must remain beatable")
                assertTrue(skilled.driftBonuses >= 10)
            }
        }
    }
}
