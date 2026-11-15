package turbotides

import kotlin.math.*

enum class Phase { GARAGE, COUNTDOWN, RACING, PAUSED, FINISHED }
enum class Difficulty(val title: String, val recordId: String, val pace: Float, val cornerCaution: Float, val response: Float) {
    // Keep the first two saved indices and record IDs compatible with 1.2.
    EASY("Easy", "CRUISE", 0.88f, 250f, 0.8f),
    MEDIUM("Medium", "RACE", 1.05f, 190f, 1f),
    HARD("Hard", "HARD", 1.20f, 150f, 1.4f),
    SUPER_HARD("Super Hard", "SUPER_HARD", 1.31f, 110f, 1.8f),
    ;

    fun next(direction: Int): Difficulty = entries[Math.floorMod(ordinal + direction, entries.size)]
}

data class Controls(
    val throttle: Boolean = false,
    val brake: Boolean = false,
    val steer: Float = 0f,
    val drift: Boolean = false,
    val boost: Boolean = false,
)

class Racer(val name: String, val paint: Int, var distance: Float, var lane: Float) {
    var speed = 0f
    var lateralSpeed = 0f
    var finishTime: Float? = null
}

class Race(val track: Track, val difficulty: Difficulty = Difficulty.EASY, paint: Int = 0) {
    companion object {
        const val STEP = 1f / 120f
        const val LAPS = 3
        const val MAX_SPEED = 62f
    }

    val player = Racer("You", paint, 0f, -3f)
    val rivals = listOf("Phippy", "Goldie", "Hazel", "Kube", "Zee").mapIndexed { i, name ->
        Racer(name, (i + 1) % 5, 7f + i / 2 * 7f, if (i % 2 == 0) 3f else -3f)
    }
    var phase = Phase.GARAGE
        private set
    private var beforePause = Phase.RACING
    var countdown = 3.4f
        private set
    var elapsed = 0f
        private set
    var nitro = 65f
        private set
    var drifting = false
        private set
    var boosting = false
        private set
    var driftCharge = 0f
        private set
    var message = ""
        private set
    var messageTime = 0f
        private set
    var messageSequence = 0
        private set
    var bumps = 0
        private set
    var pads = 0
        private set
    var driftBonuses = 0
        private set
    var bestLap: Float? = null
        private set
    private var lapStart = 0f
    private var completedLaps = 0
    private var contactCooldown = 0f
    private val padLap = IntArray(3) { -1 }
    private var padBoost = 0f
    private var accumulator = 0f
    val lap get() = (floor(player.distance / track.length).toInt() + 1).coerceIn(1, LAPS)
    val order get() = (rivals + player).sortedWith(compareBy<Racer> { it.finishTime ?: Float.MAX_VALUE }.thenByDescending { it.distance })
    val position get() = order.indexOf(player) + 1

    fun start() {
        if (phase == Phase.GARAGE) phase = Phase.COUNTDOWN
    }

    fun pause() {
        if (phase == Phase.COUNTDOWN || phase == Phase.RACING) {
            beforePause = phase
            phase = Phase.PAUSED
            accumulator = 0f
            boosting = false
        }
    }

    fun resume() {
        if (phase == Phase.PAUSED) phase = beforePause
    }

    fun advance(delta: Float, controls: Controls) {
        if (phase != Phase.COUNTDOWN && phase != Phase.RACING) return
        // A stalled window must not fast-forward the race or tunnel through cars.
        accumulator += delta.coerceIn(0f, 0.1f)
        while (accumulator >= STEP) {
            tick(controls)
            accumulator -= STEP
        }
    }

    private fun tick(controls: Controls) {
        if (phase == Phase.COUNTDOWN) {
            countdown -= STEP
            if (countdown <= 0f) {
                phase = Phase.RACING
                say("GO!", 1.4f)
            }
            return
        }
        if (phase != Phase.RACING) return
        elapsed += STEP
        messageTime = (messageTime - STEP).coerceAtLeast(0f)
        contactCooldown -= STEP
        padBoost -= STEP
        updatePlayer(controls)
        rivals.forEachIndexed { index, rival -> updateRival(rival, index) }
        resolveContacts()
        val laps = floor(player.distance / track.length).toInt()
        if (laps > completedLaps) {
            val time = elapsed - lapStart
            bestLap = min(bestLap ?: Float.MAX_VALUE, time)
            lapStart = elapsed
            completedLaps = laps
            if (laps < LAPS) say(if (laps == LAPS - 1) "Final lap!" else "Lap ${laps + 1}")
        }
        if (player.distance >= track.length * LAPS) {
            player.finishTime = elapsed
            boosting = false
            drifting = false
            phase = Phase.FINISHED
            accumulator = 0f
        }
    }

    private fun updatePlayer(input: Controls) {
        val offroad = abs(player.lane) > track.roadHalfWidth
        val wasDrifting = drifting
        drifting = input.drift && abs(input.steer) > 0.1f && player.speed > 22f && !offroad
        boosting = input.boost && nitro > 0.5f && input.throttle && !input.brake && !offroad
        val topSpeed = when {
            offroad -> 28f
            boosting || padBoost > 0 -> 87f
            drifting -> 57f
            else -> MAX_SPEED
        }
        val acceleration = when {
            input.brake -> -46f
            input.throttle -> if (boosting || padBoost > 0) 40f else 23f
            else -> -10f
        }
        if (player.speed < topSpeed || acceleration < 0f) {
            player.speed = (player.speed + acceleration * STEP).coerceAtLeast(0f)
            if (acceleration > 0f) player.speed = min(player.speed, topSpeed)
        }
        if (player.speed > topSpeed) player.speed = max(topSpeed, player.speed - 34f * STEP)
        if (boosting) nitro = max(0f, nitro - 26f * STEP) else nitro = min(100f, nitro + 3f * STEP)
        if (drifting) driftCharge += STEP
        if (wasDrifting && !drifting) {
            if (driftCharge >= 0.45f) {
                nitro = min(100f, nitro + 12f + min(driftCharge, 3f) * 10f)
                driftBonuses++
                say("Drift bonus +nitro", 1.1f)
            }
            driftCharge = 0f
        }
        val steering = input.steer.coerceIn(-1f, 1f) * (if (drifting) 14f else 11f) * (player.speed / 28f).coerceIn(0f, 1f)
        val cornerForce = cornerForce()
        val targetLateral = steering + cornerForce
        player.lateralSpeed += (targetLateral - player.lateralSpeed) * min(1f, STEP * if (drifting) 3f else 8f)
        player.lane += player.lateralSpeed * STEP
        val laneLimit = track.barrier - CarShape.lateralExtent(player, drifting)
        if (abs(player.lane) > laneLimit) {
            player.lane = player.lane.coerceIn(-laneLimit, laneLimit)
            player.lateralSpeed *= -0.4f
            if (contactCooldown <= 0f) {
                player.speed *= 0.65f
                bumps++
                contactCooldown = 0.7f
                say("Barrier bump - keep going!", 1f)
            }
        }
        player.distance += player.speed * STEP
        for (i in 0..2) {
            val currentLap = floor(player.distance / track.length).toInt()
            if (player.speed > 1f &&
                padLap[i] != currentLap &&
                abs(track.relativeDistance(player.distance, track.padDistance(i))) < 3f &&
                abs(player.lane - track.padLane(i)) < 2.2f
            ) {
                padBoost = 1.6f
                padLap[i] = currentLap
                nitro = min(100f, nitro + 16f)
                pads++
                say("Turbo pad!", 1f)
            }
        }
    }

    // Keep full steering effective even in the sharpest bend while boosting.
    fun cornerForce(): Float = (track.curvature(player.distance) * player.speed * player.speed * 0.065f).coerceIn(-4.5f, 4.5f)

    private fun updateRival(rival: Racer, index: Int) {
        if (rival.finishTime != null) return
        val bend = abs(track.curvature(rival.distance))
        val pace = (54.5f + index * 1.4f) * difficulty.pace
        val surge = if (sin(elapsed * 0.65f + index * 2f) > 0.85f) 11f else 0f
        // Difficulty changes opponent pace and corner confidence, never the
        // player's controls or a hidden catch-up multiplier. Even Super Hard
        // stays below the player's 87 m/s boosted limit.
        val target = ((pace - bend * difficulty.cornerCaution).coerceAtLeast(34f) + surge).coerceAtMost(87f)
        rival.speed += (target - rival.speed) * STEP * difficulty.response
        val preferredLane = (if (index % 2 == 0) 3.8f else -3.8f) + sin(elapsed * 0.4f + index) * 1.1f
        val laneTarget = passingLane(rival, preferredLane)
        rival.lateralSpeed = (laneTarget - rival.lane) * 2f
        rival.lane += rival.lateralSpeed * STEP
        rival.distance += rival.speed * STEP
        if (rival.distance >= track.length * LAPS) rival.finishTime = elapsed
    }

    private fun passingLane(rival: Racer, preferredLane: Float): Float {
        // Begin moving aside before braking distance closes. Keep clearance
        // until the rear bumper is past, so a lapped parked car cannot trap AI.
        val nearby = (rivals + player).filter { other ->
            val gap = track.relativeDistance(other.distance, rival.distance)
            other !== rival &&
                other.finishTime == null &&
                gap > -7f &&
                gap < 16f + max(0f, rival.speed - other.speed) * 1.5f
        }
        fun clear(lane: Float) = nearby.none { abs(lane - it.lane) < CarShape.HALF_WIDTH * 2f + 0.6f }
        if (clear(preferredLane)) return preferredLane
        return listOf(-7f, -3.5f, 0f, 3.5f, 7f)
            .filter { clear(it) }
            .minByOrNull { abs(it - rival.lane) }
            ?: rival.lane
    }

    private fun resolveContacts() {
        val cars = rivals.filter { it.finishTime == null } + player
        // A second pass resolves a car pressed between neighbours. The small
        // fixed step keeps penetration corrections below one frame of travel.
        repeat(2) {
            for (i in cars.indices) {
                for (j in i + 1 until cars.size) {
                    val a = cars[i]
                    val b = cars[j]
                    val driftA = a === player && drifting
                    val driftB = b === player && drifting
                    val distance = track.relativeDistance(a.distance, b.distance)
                    val longitudinalOverlap =
                        CarShape.longitudinalExtent(a, driftA) + CarShape.longitudinalExtent(b, driftB) - abs(distance)
                    val lateralOverlap = CarShape.lateralExtent(a, driftA) + CarShape.lateralExtent(b, driftB) - abs(a.lane - b.lane)
                    if (longitudinalOverlap <= 0f || lateralOverlap <= 0f) continue
                    if ((a === player || b === player) && contactCooldown <= 0f) {
                        player.speed *= 0.8f
                        contactCooldown = 0.8f
                        bumps++
                        say("Trading paint!", 0.8f)
                    }
                    val behind = if (distance < 0f) a else b
                    val ahead = if (distance < 0f) b else a
                    if (longitudinalOverlap < lateralOverlap && behind.distance >= longitudinalOverlap) {
                        behind.distance -= longitudinalOverlap
                        behind.speed = min(behind.speed, ahead.speed)
                    } else {
                        val side = if (a.lane < b.lane) -1f else 1f
                        val movedA = abs(moveAside(a, side * lateralOverlap / 2f, driftA))
                        val movedB = abs(moveAside(b, -side * (lateralOverlap - movedA), driftB))
                        moveAside(a, side * (lateralOverlap - movedA - movedB).coerceAtLeast(0f), driftA)
                        // Cancel only velocity into the neighbour, retaining a
                        // player's immediate ability to steer away and recover.
                        if (a.lateralSpeed * side < 0f) a.lateralSpeed = 0f
                        if (b.lateralSpeed * side > 0f) b.lateralSpeed = 0f
                    }
                }
            }
        }
    }

    private fun moveAside(racer: Racer, distance: Float, drift: Boolean): Float {
        val before = racer.lane
        val limit = track.barrier - CarShape.lateralExtent(racer, drift)
        racer.lane = (before + distance).coerceIn(-limit, limit)
        return racer.lane - before
    }

    private fun say(text: String, duration: Float = 1.8f) {
        message = text
        messageTime = duration
        messageSequence++
    }
}
