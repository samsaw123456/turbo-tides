package turbotides

import com.badlogic.gdx.Gdx
import com.badlogic.gdx.Input
import com.badlogic.gdx.graphics.*
import com.badlogic.gdx.graphics.g2d.*
import com.badlogic.gdx.graphics.g2d.freetype.FreeTypeFontGenerator
import com.badlogic.gdx.graphics.glutils.ShapeRenderer
import com.badlogic.gdx.math.Rectangle
import com.badlogic.gdx.math.Vector2
import com.badlogic.gdx.utils.Disposable
import com.badlogic.gdx.utils.viewport.FitViewport
import java.util.Locale
import kotlin.math.*

fun formatTime(seconds: Float?): String {
    if (seconds == null) return "--:--.--"
    val hundredths = (seconds * 100f).toInt()
    return String.format(Locale.ROOT, "%d:%02d.%02d", hundredths / 6000, hundredths / 100 % 60, hundredths % 100)
}

class Hud : Disposable {
    private val viewport = FitViewport(1280f, 800f)
    private val batch = SpriteBatch()
    private val shapes = ShapeRenderer()
    private val large = font("BarlowCondensed-Bold.ttf", 66)
    private val heading = font("BarlowCondensed-Bold.ttf", 42)
    private val number = font("BarlowCondensed-Bold.ttf", 100)
    private val body = font("Lato-Bold.ttf", 23)
    private val small = font("Lato-Regular.ttf", 19)
    private val icon = Texture(Gdx.files.internal("art/icon-128.png"), true)
    private val phippy = Texture(Gdx.files.internal("art/phippy.png"))
    private val portrait = TextureRegion(phippy, 20, 0, 24, 30)
    private val ink = color("20343d")
    private val cream = color("fff1d7")
    private val orange = color("ff7446")
    private val mint = color("74e0c5")
    private val muted = color("bbccc9")
    private data class Action(val rect: Rectangle, val action: (Int) -> Unit)
    private val actions = mutableListOf<Action>()
    private var focus = 8
    private var lastPhase: Phase? = null
    private val mouse = Vector2()
    private var lastMouse = Vector2(-1000f, -1000f)

    init {
        icon.setFilter(Texture.TextureFilter.MipMapLinearLinear, Texture.TextureFilter.Linear)
    }

    private fun font(file: String, size: Int): BitmapFont {
        val generator = FreeTypeFontGenerator(Gdx.files.internal("fonts/$file"))
        return generator.generateFont(
            FreeTypeFontGenerator.FreeTypeFontParameter().apply {
                this.size = size
                minFilter = Texture.TextureFilter.Linear
                magFilter = Texture.TextureFilter.Linear
            },
        ).also { generator.dispose() }
    }

    fun resize(width: Int, height: Int) {
        viewport.update(width, height, true)
    }

    private fun rect(x: Float, y: Float, w: Float, h: Float, shade: Color) {
        Gdx.gl.glEnable(GL20.GL_BLEND)
        Gdx.gl.glBlendFunc(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA)
        shapes.begin(ShapeRenderer.ShapeType.Filled)
        shapes.color = shade
        shapes.rect(x, y, w, h)
        shapes.end()
    }

    private fun text(text: String, x: Float, y: Float, font: BitmapFont = body, shade: Color = cream) {
        batch.begin()
        font.color = shade
        font.draw(batch, text, x, y)
        batch.end()
    }

    private fun centered(text: String, y: Float, font: BitmapFont = heading, shade: Color = cream) {
        val width = GlyphLayout(font, text).width
        text(text, 640f - width / 2f, y, font, shade)
    }

    private fun button(
        label: String,
        x: Float,
        y: Float,
        w: Float,
        action: (Int) -> Unit,
        primary: Boolean = false,
        h: Float = 54f,
        cycle: Boolean = false,
    ) {
        val index = actions.size
        val selected = focus == index
        val area = Rectangle(x, y, w, h)
        actions.add(Action(area, action))
        rect(x, y, w, h, if (primary) orange else Color(0.16f, 0.25f, 0.28f, 1f))
        if (selected) {
            rect(x - 5, y, 4f, h, cream)
            rect(x, y, w, 3f, cream)
        }
        text(label, x + 17, y + h / 2 + 10, body, if (primary) ink else cream)
        if (selected && cycle) text("<  >", x + w - 63, y + h / 2 + 9, small, mint)
    }

    fun draw(game: Game) {
        viewport.apply()
        batch.projectionMatrix = viewport.camera.combined
        shapes.projectionMatrix = viewport.camera.combined
        Gdx.gl.glEnable(GL20.GL_BLEND)
        Gdx.gl.glBlendFunc(GL20.GL_SRC_ALPHA, GL20.GL_ONE_MINUS_SRC_ALPHA)
        actions.clear()
        val race = game.race
        if (race.phase != lastPhase) {
            focus = if (race.phase == Phase.GARAGE) 8 else 0
            lastPhase = race.phase
        }
        mouse.set(Gdx.input.x.toFloat(), Gdx.input.y.toFloat())
        viewport.unproject(mouse)
        if (race.phase == Phase.GARAGE) garage(game) else raceHud(game)
        when (race.phase) {
            Phase.PAUSED -> pause(game)
            Phase.FINISHED -> finish(game)
            Phase.COUNTDOWN -> {
                rect(565f, 340f, 150f, 134f, Color(ink.r, ink.g, ink.b, 0.9f))
                centered(ceil(race.countdown).toInt().coerceIn(1, 3).toString(), 463f, number)
                centered("Hold W or Up to launch", 310f, body)
            }
            else -> Unit
        }
        menuInput(game)
        Gdx.gl.glDisable(GL20.GL_BLEND)
    }

    private fun garage(game: Game) {
        rect(0f, 0f, 378f, 800f, Color(ink.r, ink.g, ink.b, 0.98f))
        rect(378f, 0f, 4f, 800f, orange)
        batch.begin()
        batch.draw(icon, 24f, 720f, 52f, 52f)
        batch.end()
        text("TURBO TIDES", 90f, 761f, heading)
        text("Choose your circuit", 26f, 697f, body)
        for (circuit in Circuit.entries) {
            val y = 612f - circuit.ordinal * 62f
            val selected = circuit == game.circuit
            val focused = focus == actions.size
            actions.add(Action(Rectangle(18f, y, 340f, 57f)) { game.selectCircuit(circuit) })
            if (selected || focused) rect(18f, y, 340f, 57f, color(if (selected) "345359" else "2c444c"))
            if (selected) rect(18f, y, 4f, 57f, color(circuit.accent))
            if (focused) rect(25f, y + 2f, 326f, 2f, cream)
            text(circuit.title, 33f, y + 43f, body, if (selected) cream else muted)
            text(circuit.route, 34f, y + 22f, small, if (selected) color(circuit.accent) else muted)
            if (selected) text("< >", 312f, y + 36f, small, cream)
        }
        button("Paint: ${PAINT_NAMES[game.paint]}", 24f, 239f, 330f, { game.changePaint(it) }, h = 45f, cycle = true)
        rect(260f, 252f, 18f, 18f, color(PAINTS[game.paint]))
        button("Rivals: ${game.difficulty.title}", 24f, 185f, 330f, { game.changeDifficulty(it) }, h = 45f, cycle = true)
        button("Start race                Enter", 24f, 113f, 330f, { game.startRace() }, true, 57f)
        text("Arrows  Browse     Tab  Focus", 26f, 90f, small, muted)
        text(
            "M  Sound ${if (game.muted) "off" else "on"}    N  Motion ${if (game.reducedMotion) "reduced" else "full"}",
            26f,
            61f,
            small,
            muted,
        )
        text("F11  Fullscreen              Esc  Quit", 26f, 31f, small, muted)

        rect(406f, 657f, 850f, 119f, Color(ink.r, ink.g, ink.b, 0.94f))
        text(game.circuit.title, 428f, 758f, heading)
        text(game.circuit.route, 429f, 711f, body, color(game.circuit.accent))
        text(game.circuit.description, 429f, 680f, small, muted)
        val track = game.race.track
        text("${track.length.roundToInt()} m lap", 1035f, 752f, small)
        text("${track.elevation.roundToInt()} m elevation range", 1035f, 722f, small, muted)
        button(if (game.overview) "P  View starting grid" else "P  View whole circuit", 406f, 590f, 280f, { game.togglePreview() }, h = 45f)

        rect(406f, 24f, 850f, 134f, Color(ink.r, ink.g, ink.b, 0.94f))
        text("Three laps · ${game.difficulty.title} · Best ${formatTime(game.bestTime())}", 428f, 139f, body)
        text("W / Up   Accelerate      S / Down   Brake      A / D or Left / Right   Steer", 429f, 102f, small)
        text("Space + steer   Drift       Shift   Nitro       C   Rear view", 429f, 72f, small)
        text("Release a drift to earn nitro. Mint strips give a free boost.", 429f, 42f, small, mint)
        rect(1086f, 178f, 170f, 144f, Color(ink.r, ink.g, ink.b, 0.9f))
        drawMap(track, 1098f, 190f, 146f, 120f)
        batch.begin()
        batch.draw(portrait, 1201f, 120f, 24f, 30f)
        batch.end()
    }

    private fun raceHud(game: Game) {
        val race = game.race
        rect(24f, 677f, 224f, 100f, Color(ink.r, ink.g, ink.b, 0.92f))
        text(race.position.toString(), 42f, 769f, number)
        text("/ 6", 94f, 730f, heading, muted)
        text("Position", 155f, 739f, small)
        rect(1012f, 677f, 244f, 100f, Color(ink.r, ink.g, ink.b, 0.92f))
        text("Lap ${race.lap} / ${Race.LAPS}", 1032f, 756f, heading)
        text(formatTime(race.elapsed), 1033f, 708f, body, mint)
        centered("${game.circuit.title} · ${game.difficulty.title}", 769f, body, ink)
        if (race.phase == Phase.RACING && Gdx.input.isKeyPressed(Input.Keys.C)) {
            rect(419f, 705f, 442f, 37f, Color(ink.r, ink.g, ink.b, 0.94f))
            centered("Rear view · steering stays with the car", 731f, small)
        }
        if (race.phase == Phase.RACING) {
            rect(464f, 18f, 368f, 33f, Color(ink.r, ink.g, ink.b, 0.94f))
            text("Esc  Pause     R  Restart     M  Sound", 480f, 39f, small)
            if (race.messageTime > 0f) {
                val width = GlyphLayout(heading, race.message).width + 48
                rect(640 - width / 2f, 597f, width, 58f, Color(ink.r, ink.g, ink.b, 0.9f))
                centered(race.message, 645f, heading, mint)
            }
        }
        rect(1012f, 24f, 244f, 148f, Color(ink.r, ink.g, ink.b, 0.94f))
        text((race.player.speed * 3.6f).toInt().toString(), 1030f, 163f, number)
        text("km/h", 1179f, 89f, small, muted)
        val speedRatio = (race.player.speed / 87f).coerceIn(0f, 1f)
        for (i in 0..16) rect(1032f + i * 12f, 44f, 8f, 13f, if (i < speedRatio * 17) orange else color("3b535c"))
        rect(456f, 78f, 368f, 55f, Color(ink.r, ink.g, ink.b, 0.94f))
        text(
            if (race.boosting) {
                "NITRO!"
            } else if (race.drifting) {
                "DRIFT +"
            } else {
                "Shift  Nitro"
            },
            472f,
            116f,
            small,
            if (race.boosting) orange else mint,
        )
        rect(591f, 96f, 212f, 15f, color("3b535c"))
        rect(591f, 96f, 212f * race.nitro / 100f, 15f, if (race.boosting) orange else mint)
        if (race.drifting) text("Release Space to bank your boost", 489f, 163f, small, cream)
        minimap(race)
    }

    private fun minimap(race: Race) {
        rect(24f, 24f, 242f, 188f, Color(ink.r, ink.g, ink.b, 0.9f))
        drawMap(race.track, 42f, 53f, 205f, 145f, race)
        text("You", 37f, 53f, small, orange)
    }

    private fun drawMap(track: Track, x: Float, y: Float, width: Float, height: Float, race: Race? = null) {
        shapes.begin(ShapeRenderer.ShapeType.Filled)
        shapes.color = color("6a8588")
        val scale = min(width / (track.maxX - track.minX), height / (track.maxZ - track.minZ))
        fun map(p: Point3) = Vector2(x + width / 2 + (p.x - track.center.x) * scale, y + height / 2 + (p.z - track.center.z) * scale)
        for (i in 0 until 120) {
            val a = map(track.frame(i / 120f * track.length).center)
            val b = map(track.frame((i + 1) / 120f * track.length).center)
            shapes.rectLine(a, b, 4f)
        }
        val start = map(track.frame(0f).center)
        shapes.color = cream
        shapes.rect(start.x - 3f, start.y - 3f, 6f, 6f)
        if (race != null) {
            for (racer in race.rivals.filter { it.finishTime == null } + race.player) {
                val p = map(track.frame(racer.distance).center)
                shapes.color = if (racer == race.player) orange else cream
                shapes.circle(p.x, p.y, if (racer == race.player) 5.8f else 3f, 12)
            }
        }
        shapes.end()
    }

    private fun pause(game: Game) {
        rect(0f, 0f, 1280f, 800f, Color(0.06f, 0.13f, 0.16f, 0.65f))
        rect(405f, 183f, 470f, 448f, ink)
        text("Race paused", 442f, 597f, large)
        text("${game.difficulty.title} rivals · Three laps", 442f, 521f, small, muted)
        button("Resume                       Esc", 443f, 429f, 394f, { game.race.resume() }, true)
        button("Restart race                   R", 443f, 358f, 394f, { game.startRace() })
        button("Back to garage", 443f, 287f, 394f, { game.garage() })
        text(
            "M  Sound: ${if (game.muted) "off" else "on"}     N  Reduced motion: ${if (game.reducedMotion) "on" else "off"}",
            442f,
            247f,
            small,
            muted,
        )
    }

    private fun finish(game: Game) {
        val race = game.race
        rect(0f, 0f, 1280f, 800f, Color(0.06f, 0.13f, 0.16f, 0.55f))
        rect(328f, 90f, 624f, 620f, ink)
        val title = when (race.position) {
            1 -> "Victory!"
            2, 3 -> "On the podium!"
            else -> "Finish line crossed!"
        }
        text(title, 368f, 678f, large, if (race.position == 1) mint else cream)
        text("${race.position} of 6  ·  ${game.circuit.title} · ${game.difficulty.title}", 370f, 604f, body)
        text(formatTime(race.elapsed), 368f, 558f, large, orange)
        text(if (game.newBest) "New personal best!" else "Best  ${formatTime(game.bestTime())}", 651f, 540f, body, mint)
        text("Best lap  ${formatTime(race.bestLap)}", 370f, 474f, small, muted)
        text("${race.driftBonuses} drift bonuses    ${race.pads} turbo pads", 370f, 441f, small, muted)
        race.order.take(3).forEachIndexed { index, racer ->
            val y = 392f - index * 35f
            text("${index + 1}    ${racer.name}", 371f, y, body, if (racer == race.player) orange else cream)
            text(racer.finishTime?.let(::formatTime) ?: "On course", 744f, y, small, muted)
        }
        button("Race again", 370f, 205f, 255f, { game.startRace() }, true)
        button("Garage", 650f, 205f, 260f, { game.garage() })
        text("Enter  Choose      Left / Right  Switch      R  Retry", 370f, 164f, small, muted)
        if (game.saveError) text("Record could not be saved on this computer.", 370f, 128f, small, orange)
    }

    private fun menuInput(game: Game) {
        if (actions.isEmpty()) return
        if (!mouse.epsilonEquals(lastMouse, 0.1f)) {
            val hovered = actions.indexOfFirst { it.rect.contains(mouse) }
            if (hovered >= 0) focus = hovered
        }
        lastMouse.set(mouse)
        val garage = lastPhase == Phase.GARAGE
        val oldFocus = focus
        if (Gdx.input.isKeyJustPressed(Input.Keys.TAB)) {
            val direction = if (Gdx.input.isKeyPressed(Input.Keys.SHIFT_LEFT) || Gdx.input.isKeyPressed(Input.Keys.SHIFT_RIGHT)) -1 else 1
            focus = Math.floorMod(focus + direction, actions.size)
        }
        if (Gdx.input.isKeyJustPressed(Input.Keys.DOWN)) focus = (focus + 1) % actions.size
        if (Gdx.input.isKeyJustPressed(Input.Keys.UP)) focus = (focus - 1 + actions.size) % actions.size
        focus = focus.coerceIn(0, actions.lastIndex)
        if (garage && focus < Circuit.entries.size && focus != oldFocus) game.selectCircuit(Circuit.entries[focus])
        val left = Gdx.input.isKeyJustPressed(Input.Keys.LEFT)
        val right = Gdx.input.isKeyJustPressed(Input.Keys.RIGHT)
        if (left || right) {
            if (garage && (focus < Circuit.entries.size || focus == 8)) {
                if (focus < Circuit.entries.size) game.selectCircuit(Circuit.entries[focus])
                game.changeCircuit(if (left) -1 else 1)
                if (focus < Circuit.entries.size) focus = game.circuit.ordinal
            } else if (garage) {
                actions[focus].action(if (left) -1 else 1)
            } else {
                focus = (focus + (if (left) -1 else 1) + actions.size) % actions.size
            }
        }
        if (Gdx.input.isKeyJustPressed(Input.Keys.ENTER)) {
            if (garage && focus < Circuit.entries.size) {
                game.selectCircuit(Circuit.entries[focus])
                game.startRace()
            } else {
                actions[focus].action(1)
            }
        }
        if (Gdx.input.isButtonJustPressed(Input.Buttons.LEFT)) actions.firstOrNull { it.rect.contains(mouse) }?.action?.invoke(1)
    }

    override fun dispose() {
        listOf(large, heading, number, body, small).forEach { it.dispose() }
        icon.dispose()
        phippy.dispose()
        shapes.dispose()
        batch.dispose()
    }
}
