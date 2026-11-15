package turbotides

import com.badlogic.gdx.Gdx
import com.badlogic.gdx.graphics.*
import com.badlogic.gdx.graphics.g3d.*
import com.badlogic.gdx.graphics.g3d.attributes.ColorAttribute
import com.badlogic.gdx.graphics.g3d.environment.DirectionalLight
import com.badlogic.gdx.graphics.g3d.utils.MeshPartBuilder
import com.badlogic.gdx.graphics.g3d.utils.ModelBuilder
import com.badlogic.gdx.math.Matrix4
import com.badlogic.gdx.math.Vector3
import com.badlogic.gdx.utils.Disposable
import kotlin.math.*
import kotlin.random.Random

val PAINTS = listOf("ff653b", "32b7ae", "f8ca55", "ebf0e8", "7888d4")
val PAINT_NAMES = listOf("Tangerine", "Lagoon", "Sunshine", "Pearl", "Bluebird")
fun color(hex: String): Color = Color.valueOf(hex)
fun Point3.vector() = Vector3(x, y, z)

class World(var track: Track) : Disposable {
    val camera = PerspectiveCamera(67f, 1280f, 800f)
    private val batch = ModelBatch()
    private val environment = Environment()
    private val models = mutableListOf<Model>()
    private val scenery: List<ModelInstance>
    private val carModels = PAINTS.map { createCar(color(it)) }
    private val cars = List(5) { ModelInstance(carModels[(it + 1) % carModels.size]) }
    private var playerCar = ModelInstance(carModels[0])
    private val shadowModel = solidModel { part ->
        part.setColor(color("253c42"))
        part.ellipse(3.2f, 5.4f, 16, 0f, 0f, 0f, 0f, 1f, 0f)
    }
    private val shadow = ModelInstance(shadowModel)
    private val flameModel = solidModel { part ->
        part.setColor(color("ffba42"))
        part.setVertexTransform(Matrix4().rotate(Vector3.X, -90f))
        part.cone(0.65f, 2.6f, 0.65f, 7)
    }
    private val flames = List(2) { ModelInstance(flameModel) }
    private val sun = ModelInstance(
        solidModel { part ->
            part.setColor(color("ffe5a2"))
            part.setVertexTransform(Matrix4().translate(-300f, 220f, -470f))
            part.sphere(95f, 95f, 95f, 20, 12)
        },
    )
    private var cameraReady = false
    private var wasRearView = false
    private var clock = 0f
    private var paintIndex = -1
    private val target = Vector3()
    private val cameraTarget = Vector3()
    private val previousPlayerPosition = Vector3()
    private val sky get() = color(
        when (track.circuit) {
            Circuit.SUNSET -> "edc7a2"
            Circuit.CINDER -> "d8b79b"
            Circuit.SAN_FRANCISCO -> "c8d6cf"
            Circuit.SILICON_VALLEY -> "d2dfce"
            Circuit.NEW_YORK -> "ced7d6"
            Circuit.CHICAGO -> "c2d8df"
        },
    )

    init {
        environment.set(ColorAttribute(ColorAttribute.AmbientLight, 0.48f, 0.5f, 0.54f, 1f))
        environment.add(DirectionalLight().set(0.68f, 0.63f, 0.55f, -0.5f, -1f, 0.3f))
        environment.set(ColorAttribute(ColorAttribute.Fog, sky))
        camera.near = 0.2f
        camera.far = 1400f
        // Separate city meshes from road meshes to stay below index limits.
        scenery = listOf(ModelInstance(createCircuit()), ModelInstance(solidModel { CityScenery(track).build(it) }))
    }

    private fun solidModel(build: (MeshPartBuilder) -> Unit): Model {
        val builder = ModelBuilder()
        builder.begin()
        val part = builder.part(
            "geometry",
            GL20.GL_TRIANGLES,
            (VertexAttributes.Usage.Position or VertexAttributes.Usage.Normal or VertexAttributes.Usage.ColorUnpacked).toLong(),
            Material(ColorAttribute.createDiffuse(Color.WHITE)),
        )
        build(part)
        return builder.end().also { models.add(it) }
    }

    private fun box(part: MeshPartBuilder, shade: String, x: Float, y: Float, z: Float, w: Float, h: Float, d: Float, yaw: Float = 0f) {
        Geometry(part).box(shade, Point3(x, y, z), w, h, d, yaw)
    }

    private fun quad(part: MeshPartBuilder, a: Point3, b: Point3, c: Point3, d: Point3, shade: String) {
        Geometry(part).quad(a, b, c, d, shade)
    }

    private fun createCircuit(): Model = solidModel { part ->
        val sunset = track.circuit == Circuit.SUNSET
        val natural = track.circuit == Circuit.SUNSET || track.circuit == Circuit.CINDER
        val land = when (track.circuit) {
            Circuit.CINDER -> "bc805e"
            Circuit.NEW_YORK -> "b1b3a2"
            Circuit.SAN_FRANCISCO -> "b3bd94"
            else -> "91ab78"
        }
        // Fog is evaluated at vertices. Subdivide the sea so its near surface
        // keeps its colour instead of inheriting fog from far-away corners.
        for (x in -10 until 10) {
            for (z in -10 until 10) {
                val a = Point3(x * 100f, -5f, z * 100f)
                quad(
                    part,
                    a,
                    a + Point3(0f, 0f, 100f),
                    a + Point3(100f, 0f, 100f),
                    a + Point3(100f, 0f, 0f),
                    if (sunset) {
                        "329f9d"
                    } else if (track.circuit == Circuit.CHICAGO) {
                        "428fa7"
                    } else {
                        "568d91"
                    },
                )
            }
        }
        val segments = 360
        val step = track.length / segments
        for (i in 0 until segments) {
            val a = track.frame(i * step)
            val b = track.frame((i + 1) * step)
            quad(part, a.at(-9f), b.at(-9f), b.at(9f), a.at(9f), if (i % 7 == 0) "465159" else "424d55")
            for (side in listOf(-1f, 1f)) {
                val edge = 9f * side
                val curb = 10f * side
                val shoulder = 13.4f * side
                val shore = (if (natural || track.circuit == Circuit.CHICAGO) 38f else 95f) * side
                val curbColor = if (i % 4 < 2) "fff0cd" else "e77850"
                if (side < 0) {
                    quad(part, a.at(edge, 0.04f), b.at(edge, 0.04f), b.at(curb, 0.04f), a.at(curb, 0.04f), curbColor)
                    quad(
                        part,
                        a.at(curb, -0.05f),
                        b.at(curb, -0.05f),
                        b.at(shoulder, -0.05f),
                        a.at(shoulder, -0.05f),
                        land,
                    )
                    quad(
                        part,
                        a.at(shoulder, -0.1f),
                        b.at(shoulder, -0.1f),
                        b.at(shore).copy(y = -3f),
                        a.at(shore).copy(y = -3f),
                        if (natural) {
                            if (sunset) "d7ab79" else "b57356"
                        } else {
                            land
                        },
                    )
                } else {
                    quad(part, a.at(curb, 0.04f), b.at(curb, 0.04f), b.at(edge, 0.04f), a.at(edge, 0.04f), curbColor)
                    quad(
                        part,
                        a.at(shoulder, -0.05f),
                        b.at(shoulder, -0.05f),
                        b.at(curb, -0.05f),
                        a.at(curb, -0.05f),
                        land,
                    )
                    quad(
                        part,
                        Point3(0f, 1f, 0f),
                        b.at(shoulder, -0.1f),
                        a.at(shoulder, -0.1f),
                        Point3(0f, 1f, 0f),
                        land,
                    )
                }
                if (i % 2 == 0) {
                    val p = a.at(13.4f * side, 0.65f)
                    box(part, if (i % 8 < 4) "e3d7b9" else "cf784e", p.x, p.y, p.z, 0.55f, 1.3f, step * 2.03f, a.heading)
                }
                if (i % 4 < 2) {
                    val line = 8.4f * side
                    quad(
                        part,
                        a.at(line - 0.09f, 0.055f),
                        b.at(line - 0.09f, 0.055f),
                        b.at(line + 0.09f, 0.055f),
                        a.at(line + 0.09f, 0.055f),
                        "e7e2ce",
                    )
                }
            }
            if (i % 6 < 3) quad(part, a.at(-0.09f, 0.06f), b.at(-0.09f, 0.06f), b.at(0.09f, 0.06f), a.at(0.09f, 0.06f), "f7df9d")
        }
        // Start line tiles follow the same sampled surface as the cars.
        for (row in 0..1) {
            for (column in 0..11) {
                val a = track.frame(row * 1.5f)
                val b = track.frame((row + 1) * 1.5f)
                val x = -9f + column * 1.5f
                quad(
                    part,
                    a.at(x, 0.08f),
                    b.at(x, 0.08f),
                    b.at(x + 1.5f, 0.08f),
                    a.at(x + 1.5f, 0.08f),
                    if ((row + column) % 2 ==
                        0
                    ) {
                        "fff7db"
                    } else {
                        "25373e"
                    },
                )
            }
        }
        for (i in 0..2) {
            val d = track.padDistance(i)
            val lane = track.padLane(i)
            for (j in 0..3) {
                val a = track.frame(d - 3f + j * 1.6f)
                val b = track.frame(d - 2.2f + j * 1.6f)
                quad(part, a.at(lane - 1.8f, 0.09f), b.at(lane - 1.8f, 0.09f), b.at(lane + 1.8f, 0.09f), a.at(lane + 1.8f, 0.09f), "6de7ce")
            }
        }
        val start = track.frame(0f)
        for (side in listOf(-1f, 1f)) {
            val p = start.at(side * 11.5f, 5f)
            box(part, "f3e2c5", p.x, p.y, p.z, 0.7f, 10f, 0.7f)
        }
        val banner = start.at(0f, 10f)
        box(part, "ff6a42", banner.x, banner.y, banner.z, 24f, 2f, 0.7f, start.heading)
        for (i in -5..5) {
            val p = start.at(i * 1.9f, 10f)
            box(part, if (i % 2 == 0) "fff0cd" else "273b43", p.x, p.y, p.z, 1.5f, 0.7f, 0.74f, start.heading)
        }
        val random = Random(if (sunset) 32 else 71)
        if (natural) {
            for (i in 0 until 95) {
                val frame = track.frame(i / 95f * track.length + 12f)
                val p = frame.at(if (i % 3 == 0) 18f + random.nextFloat() * 13f else -19f - random.nextFloat() * 5f, -1.5f)
                if (sunset) {
                    palm(part, p, 6f + random.nextFloat() * 5f, random.nextFloat() * 360f)
                } else {
                    rock(part, p, 3f + random.nextFloat() * 8f, random.nextFloat() * 360f)
                }
            }
            for (i in 0..13) {
                val angle = i * 2.4f
                val p = Point3(cos(angle) * 50f, 0f, sin(angle) * 45f)
                val height = 23f + random.nextFloat() * 39f
                part.setColor(color(if (sunset) "779479" else "aa6c54"))
                part.setVertexTransform(Matrix4().translate(p.x, height / 2f, p.z).rotate(Vector3.Y, i * 31f))
                part.cone(42f, height, 44f, 5)
            }
        }
        for (i in 0..18) {
            val angle = i * 0.71f
            val x = cos(angle) * 520f
            val z = sin(angle) * 520f
            box(part, "f7e4c7", x, 95f + i % 4 * 13f, z, 48f + i % 3 * 25f, 7f, 20f, i * 16f)
        }
    }

    private fun palm(part: MeshPartBuilder, p: Point3, height: Float, angle: Float) {
        box(part, "957353", p.x, p.y + height / 2f, p.z, 0.65f, height, 0.65f, angle)
        for (i in 0..4) {
            part.setColor(color(if (i % 2 == 0) "397f69" else "68a174"))
            part.setVertexTransform(
                Matrix4().translate(p.x, p.y + height, p.z).rotate(Vector3.Y, angle + i * 72f).rotate(Vector3.X, 12f).translate(0f, 0f, 2f),
            )
            part.box(1.6f, 0.18f, 5.4f)
        }
    }

    private fun rock(part: MeshPartBuilder, p: Point3, height: Float, angle: Float) {
        part.setColor(color("a46349"))
        part.setVertexTransform(Matrix4().translate(p.x, p.y + height / 2, p.z).rotate(Vector3.Y, angle))
        part.cone(height * 0.7f, height, height * 0.7f, 5)
        box(part, "d79868", p.x, p.y + height * 0.4f, p.z, height * 0.45f, height * 0.2f, height * 0.5f, angle)
    }

    private fun createCar(paint: Color): Model = solidModel { part ->
        box(part, "23353c", 0f, 0.48f, 0f, 2.05f, 0.42f, 4.2f)
        part.setColor(paint)
        part.setVertexTransform(Matrix4().translate(0f, 0.86f, 0f))
        part.box(2.05f, 0.48f, 3.9f)
        part.setVertexTransform(Matrix4().translate(0f, 1.3f, -0.3f))
        part.box(1.6f, 0.56f, 1.8f)
        box(part, "254650", 0f, 1.34f, 0.62f, 1.38f, 0.42f, 0.06f)
        box(part, "254650", 0f, 1.34f, -1.22f, 1.38f, 0.4f, 0.06f)
        box(part, "254650", -0.81f, 1.32f, -0.3f, 0.05f, 0.36f, 1.5f)
        box(part, "254650", 0.81f, 1.32f, -0.3f, 0.05f, 0.36f, 1.5f)
        box(part, "f8e8c4", 0f, 1.115f, 1.2f, 0.37f, 0.03f, 1.4f)
        box(part, "f8e8c4", 0f, 1.59f, -0.3f, 0.37f, 0.03f, 1.85f)
        box(part, "22343c", 0f, 1.4f, -1.8f, 2.4f, 0.16f, 0.5f)
        for (side in listOf(-1f, 1f)) {
            box(part, "253b43", side * 0.78f, 1.14f, -1.8f, 0.12f, 0.5f, 0.15f)
            box(part, "fff1b8", side * 0.66f, 0.84f, 1.97f, 0.52f, 0.23f, 0.06f)
            box(part, "f3483c", side * 0.68f, 0.82f, -1.97f, 0.5f, 0.2f, 0.06f)
            for (z in listOf(-1.3f, 1.25f)) {
                part.setColor(color("1d2b32"))
                part.setVertexTransform(Matrix4().translate(side * 1.05f, 0.51f, z).rotate(Vector3.Z, 90f))
                part.cylinder(0.92f, 0.42f, 0.92f, 12)
                part.setColor(color("c9d3ce"))
                part.setVertexTransform(Matrix4().translate(side * 1.28f, 0.51f, z).rotate(Vector3.Z, 90f))
                part.cylinder(0.51f, 0.025f, 0.51f, 8)
            }
        }
    }

    fun resize(width: Int, height: Int) {
        camera.viewportWidth = width.toFloat()
        camera.viewportHeight = height.toFloat()
        camera.update()
    }

    fun resetCamera() {
        cameraReady = false
    }

    fun render(race: Race, delta: Float, reducedMotion: Boolean, rearView: Boolean, overview: Boolean = true) {
        clock += delta
        val player = race.player
        val frame = track.frame(player.distance)
        val p = frame.at(player.lane, 0.1f)
        val inGarage = race.phase == Phase.GARAGE
        val direction = frame.forward
        val touring = inGarage && overview
        val angle = track.circuit.previewAngle + if (reducedMotion) 0f else sin(clock * 0.055f) * 0.27f
        val tourEye = track.center + Point3(cos(angle) * track.radius * 2.05f, track.radius * 1.55f, sin(angle) * track.radius * 2.05f)
        val tourRight = RoadFrame(track.center, (track.center - tourEye).normal()).right
        // Offset both eye and target so the circuit sits beside the selector.
        val tourOffset = tourRight * (-track.radius * 0.73f)
        val gridEye = p + frame.right * (10f + if (reducedMotion) 0f else sin(clock * 0.16f) * 2f) + direction * 12f + Point3(0f, 6f, 0f)
        val gridOffset = RoadFrame(p, (p - gridEye).normal()).right * -4.8f
        val cameraPosition = if (touring) {
            tourEye + tourOffset
        } else if (inGarage) {
            gridEye + gridOffset
        } else {
            p + direction * (if (rearView) 12f else -12f) + Point3(0f, 5.8f, 0f)
        }
        val look = if (touring) {
            track.center + tourOffset
        } else if (inGarage) {
            p + gridOffset
        } else {
            p + direction * (if (rearView) -14f else 17f) + Point3(0f, 1.5f, 0f)
        }
        target.set(cameraPosition.vector())
        val smoothing = if (reducedMotion) 16f else 8f
        if (!cameraReady || inGarage || rearView || rearView != wasRearView) {
            camera.position.set(target)
            cameraTarget.set(look.vector())
            cameraReady = true
        } else {
            // Carry the camera with the car before smoothing its relative pose.
            // Otherwise a fast car outruns a lerped camera and shrinks on screen.
            val movement = p.vector().sub(previousPlayerPosition)
            camera.position.add(movement)
            cameraTarget.add(movement)
            camera.position.lerp(target, 1f - exp(-delta * smoothing))
            cameraTarget.lerp(look.vector(), 1f - exp(-delta * 12f))
        }
        previousPlayerPosition.set(p.vector())
        wasRearView = rearView
        camera.up.set(Vector3.Y)
        camera.lookAt(cameraTarget)
        camera.fieldOfView += ((if (race.boosting && !reducedMotion) 76f else 67f) - camera.fieldOfView) * min(1f, delta * 4f)
        camera.update()
        val bg = sky
        Gdx.gl.glViewport(0, 0, Gdx.graphics.width, Gdx.graphics.height)
        Gdx.gl.glClearColor(bg.r, bg.g, bg.b, 1f)
        Gdx.gl.glClear(GL20.GL_COLOR_BUFFER_BIT or GL20.GL_DEPTH_BUFFER_BIT)
        batch.begin(camera)
        batch.render(sun)
        batch.render(scenery, environment)
        if (paintIndex != player.paint) {
            playerCar = ModelInstance(carModels[player.paint])
            paintIndex = player.paint
        }
        renderCar(playerCar, player, race.drifting)
        if (!inGarage) race.rivals.forEachIndexed { index, rival -> if (rival.finishTime == null) renderCar(cars[index], rival, false) }
        if (race.boosting) {
            for (i in 0..1) {
                val flame = flames[i]
                flame.transform.setToTranslation(p.vector()).rotate(Vector3.Y, frame.heading)
                    .translate(if (i == 0) -0.65f else 0.65f, 0.65f, -2.7f)
                    .scale(1f, 1f, 0.7f + sin(clock * 48f) * 0.2f)
                batch.render(flame, environment)
            }
        }
        batch.end()
    }

    private fun renderCar(instance: ModelInstance, racer: Racer, drift: Boolean) {
        val frame = track.frame(racer.distance)
        val p = frame.at(racer.lane, 0.12f)
        val pitch =
            -atan2(frame.forward.y, sqrt(frame.forward.x * frame.forward.x + frame.forward.z * frame.forward.z)) * 180f / PI.toFloat()
        shadow.transform.setToTranslation(frame.at(racer.lane, 0.05f).vector()).rotate(Vector3.Y, frame.heading)
        batch.render(shadow, environment)
        instance.transform.setToTranslation(p.vector()).rotate(Vector3.Y, frame.heading - racer.lateralSpeed * if (drift) 2.7f else 0.7f)
            .rotate(Vector3.X, pitch).rotate(Vector3.Z, racer.lateralSpeed * 0.25f)
        batch.render(instance, environment)
    }

    override fun dispose() {
        batch.dispose()
        models.forEach { it.dispose() }
    }
}
