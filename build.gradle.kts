plugins {
    kotlin("jvm") version "2.2.21"
    application
    id("org.jlleitschuh.gradle.ktlint") version "13.1.0"
}

group = "turbotides"
version = file("VERSION").readText().trim()

repositories { mavenCentral() }

val gdxVersion = "1.14.2"
dependencies {
    implementation("com.badlogicgames.gdx:gdx:$gdxVersion")
    implementation("com.badlogicgames.gdx:gdx-backend-lwjgl3:$gdxVersion")
    implementation("com.badlogicgames.gdx:gdx-freetype:$gdxVersion")
    runtimeOnly("com.badlogicgames.gdx:gdx-platform:$gdxVersion:natives-desktop")
    runtimeOnly("com.badlogicgames.gdx:gdx-freetype-platform:$gdxVersion:natives-desktop")
    testImplementation(kotlin("test"))
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

kotlin { jvmToolchain(17) }
application { mainClass.set("turbotides.DesktopKt") }
tasks.test { useJUnitPlatform() }
tasks.register<Jar>("fatJar") {
    group = "build"
    archiveFileName.set("turbo-tides.jar")
    manifest { attributes["Main-Class"] = application.mainClass.get() }
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    from(sourceSets.main.get().output)
    dependsOn(configurations.runtimeClasspath)
    from({ configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) } })
    exclude("META-INF/*.SF", "META-INF/*.RSA", "META-INF/*.DSA", "module-info.class")
}
