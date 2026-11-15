package turbotides

import com.badlogic.gdx.math.Vector3
import com.badlogic.gdx.utils.GdxNativesLoader
import kotlin.test.Test
import kotlin.test.assertTrue

class GeometryTest {
    @Test fun `bridge cable sections meet their anchors at different slopes`() {
        GdxNativesLoader.load()
        val anchor = Point3(34f, 42f, 18f)
        for (end in listOf(Point3(39f, 40f, 17f), Point3(33f, 49f, 20f), Point3(34f, 5f, 18f))) {
            val transform = beamTransform(anchor, end)
            val halfLength = (end - anchor).length() / 2f
            assertTrue(Vector3(0f, -halfLength, 0f).mul(transform).dst(anchor.vector()) < 0.001f)
            assertTrue(Vector3(0f, halfLength, 0f).mul(transform).dst(end.vector()) < 0.001f)
        }
    }
}
