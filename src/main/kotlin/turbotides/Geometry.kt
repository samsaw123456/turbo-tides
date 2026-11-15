package turbotides

import com.badlogic.gdx.graphics.g3d.utils.MeshPartBuilder
import com.badlogic.gdx.math.Matrix4
import com.badlogic.gdx.math.Vector3

internal fun beamTransform(a: Point3, b: Point3): Matrix4 {
    val direction = b.vector().sub(a.vector()).nor()
    val transform = Matrix4().translate((a + b).vector().scl(0.5f))
    // Antiparallel vectors have no cross-product axis; choose X explicitly.
    return if (direction.y < -0.99999f) transform.rotate(Vector3.X, 180f) else transform.rotate(Vector3.Y, direction)
}

/** Small shared vocabulary for the hand-built road and city scenery. */
class Geometry(private val part: MeshPartBuilder) {
    fun box(shade: String, p: Point3, w: Float, h: Float, d: Float, yaw: Float = 0f) {
        part.setColor(color(shade))
        part.setVertexTransform(Matrix4().translate(p.vector()).rotate(Vector3.Y, yaw))
        part.box(w, h, d)
    }

    fun cone(shade: String, p: Point3, w: Float, h: Float, d: Float, sides: Int = 4, yaw: Float = 45f) {
        part.setColor(color(shade))
        part.setVertexTransform(Matrix4().translate(p.vector()).rotate(Vector3.Y, yaw))
        part.cone(w, h, d, sides)
    }

    fun beam(shade: String, a: Point3, b: Point3, width: Float) {
        val difference = b.vector().sub(a.vector())
        part.setColor(color(shade))
        part.setVertexTransform(beamTransform(a, b))
        part.box(width, difference.len(), width)
    }

    fun quad(a: Point3, b: Point3, c: Point3, d: Point3, shade: String) {
        part.setVertexTransform(Matrix4())
        part.setColor(color(shade))
        // Keep the upward face visible regardless of which side of the road
        // generated it. This also works for terrain fans with d == a.
        val normal = b.vector().sub(a.vector()).crs(c.vector().sub(a.vector()))
        if (normal.y < 0f) {
            part.rect(d.vector(), c.vector(), b.vector(), a.vector(), normal.scl(-1f).nor())
        } else {
            part.rect(a.vector(), b.vector(), c.vector(), d.vector(), normal.nor())
        }
    }

    fun tree(p: Point3, size: Float = 1f) {
        box("796750", p + Point3(0f, 2.5f * size, 0f), 0.8f * size, 5f * size, 0.8f * size)
        cone("497a59", p + Point3(0f, 6f * size, 0f), 7f * size, 9f * size, 7f * size, 7)
        cone("729867", p + Point3(0f, 8f * size, 0f), 5f * size, 6f * size, 5f * size, 7)
    }

    fun building(p: Point3, w: Float, h: Float, d: Float, shade: String, yaw: Float = 0f, windows: Boolean = true) {
        box("a49b86", p + Point3(0f, -2f, 0f), w + 2f, 5f, d + 2f, yaw)
        box(shade, p + Point3(0f, h / 2f, 0f), w, h, d, yaw)
        box("dcd4bd", p + Point3(0f, h, 0f), w + 0.7f, 0.7f, d + 0.7f, yaw)
        if (!windows) return
        val rotation = Matrix4().rotate(Vector3.Y, yaw)
        val floors = (h / 6f).toInt().coerceIn(1, 12)
        for (floor in 1..floors) {
            val y = floor * h / (floors + 1)
            for (side in listOf(-1f, 1f)) {
                val local = Vector3(0f, y, side * (d / 2f + 0.08f)).mul(rotation)
                box("9ebcbd", p + Point3(local.x, local.y, local.z), w * 0.8f, 1.5f, 0.12f, yaw)
            }
        }
    }
}
