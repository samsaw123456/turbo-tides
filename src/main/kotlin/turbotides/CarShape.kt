package turbotides

import kotlin.math.*

/** The complete visible car, including wheels, shared by contact and rendering. */
object CarShape {
    const val HALF_WIDTH = 1.3f
    const val HALF_LENGTH = 2.1f
    private const val HEIGHT = 1.6f

    fun yawOffset(lateralSpeed: Float, drift: Boolean): Float = -lateralSpeed * if (drift) 2.7f else 0.7f
    fun rollOffset(lateralSpeed: Float): Float = lateralSpeed * 0.25f

    fun lateralExtent(racer: Racer, drift: Boolean): Float {
        val yaw = yawOffset(racer.lateralSpeed, drift) * PI.toFloat() / 180f
        return HALF_WIDTH * abs(cos(yaw)) + HALF_LENGTH * abs(sin(yaw)) + rollMargin(racer)
    }

    fun longitudinalExtent(racer: Racer, drift: Boolean): Float {
        val yaw = yawOffset(racer.lateralSpeed, drift) * PI.toFloat() / 180f
        return HALF_LENGTH * abs(cos(yaw)) + HALF_WIDTH * abs(sin(yaw)) + rollMargin(racer)
    }

    private fun rollMargin(racer: Racer): Float = HEIGHT * abs(sin(rollOffset(racer.lateralSpeed) * PI.toFloat() / 180f))
}
