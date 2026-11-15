package turbotides

import kotlin.math.*

data class Point3(val x: Float, val y: Float, val z: Float) {
    operator fun plus(other: Point3) = Point3(x + other.x, y + other.y, z + other.z)
    operator fun minus(other: Point3) = Point3(x - other.x, y - other.y, z - other.z)
    operator fun times(scale: Float) = Point3(x * scale, y * scale, z * scale)
    fun length() = sqrt(x * x + y * y + z * z)
    fun normal(): Point3 = this * (1f / length().coerceAtLeast(0.0001f))
}

data class RoadFrame(val center: Point3, val forward: Point3) {
    val right = Point3(forward.z, 0f, -forward.x).normal()
    val heading = atan2(forward.x, forward.z) * 180f / PI.toFloat()
    fun at(lane: Float, height: Float = 0f) = center + right * lane + Point3(0f, height, 0f)
}

enum class Circuit(val title: String, val description: String) {
    SUNSET("Sunset Run", "Ocean air. Wide corners. Full throttle."),
    CINDER("Cinder Ring", "Red rock. Rolling hills. Tighter turns."),
}

class Track(val circuit: Circuit) {
    val roadHalfWidth = 9f
    val barrier = 13f
    private val points: List<Point3>
    private val distances: FloatArray
    val length: Float

    init {
        // Dense source samples are indexed by distance, not angle: speed stays
        // constant even through differently sized bends and elevated sections.
        points = (0..1024).map { i ->
            val angle = i / 1024f * PI.toFloat() * 2f
            when (circuit) {
                Circuit.SUNSET -> Point3(
                    170f * cos(angle) + 26f * cos(3f * angle),
                    7f + 4.5f * sin(2f * angle),
                    122f * sin(angle) + 16f * sin(3f * angle),
                )
                Circuit.CINDER -> Point3(
                    154f * cos(angle) + 33f * cos(2f * angle),
                    12f + 8f * sin(3f * angle),
                    133f * sin(angle) + 24f * sin(2f * angle),
                )
            }
        }
        distances = FloatArray(points.size)
        for (i in 1..points.lastIndex) distances[i] = distances[i - 1] + (points[i] - points[i - 1]).length()
        length = distances.last()
    }

    fun wrap(distance: Float): Float = ((distance % length) + length) % length

    private fun point(distance: Float): Point3 {
        val d = wrap(distance)
        val search = distances.binarySearch(d)
        val index = (if (search >= 0) search else -search - 2).coerceIn(0, points.lastIndex - 1)
        val fraction = (d - distances[index]) / (distances[index + 1] - distances[index])
        return points[index] + (points[index + 1] - points[index]) * fraction
    }

    fun frame(distance: Float): RoadFrame = RoadFrame(point(distance), (point(distance + 0.6f) - point(distance - 0.6f)).normal())

    fun curvature(distance: Float): Float {
        val before = frame(distance - 3f).forward
        val after = frame(distance + 3f).forward
        return (before.z * after.x - before.x * after.z) / 6f
    }

    fun padDistance(index: Int) = length * (0.15f + index * 0.25f)
    fun padLane(index: Int) = if (index % 2 == 0) -3.6f else 3.6f
    fun relativeDistance(a: Float, b: Float) = wrap(a - b + length / 2f) - length / 2f
}
