import java.util.Base64

plugins {
    kotlin("jvm") version "2.4.21"
    application
    id("org.jlleitschuh.gradle.ktlint") version "14.2.0"
}

group = "turbotides"
version = file("VERSION").readText().trim()

repositories { mavenCentral() }

val gdxVersion = "1.14.2"
dependencies {
    // Keep every LWJGL module and native classifier on the Java 25 compatible release.
    implementation(platform("org.lwjgl:lwjgl-bom:3.4.3"))
    implementation("com.badlogicgames.gdx:gdx:$gdxVersion")
    implementation("com.badlogicgames.gdx:gdx-backend-lwjgl3:$gdxVersion")
    implementation("com.badlogicgames.gdx:gdx-freetype:$gdxVersion")
    runtimeOnly("com.badlogicgames.gdx:gdx-platform:$gdxVersion:natives-desktop")
    runtimeOnly("com.badlogicgames.gdx:gdx-freetype-platform:$gdxVersion:natives-desktop")
    testImplementation(kotlin("test"))
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

kotlin {
    jvmToolchain {
        languageVersion.set(JavaLanguageVersion.of(25))
        vendor.set(JvmVendorSpec.ADOPTIUM)
    }
}
application {
    mainClass.set("turbotides.DesktopKt")
    applicationDefaultJvmArgs = listOf(
        "--enable-native-access=ALL-UNNAMED",
        "--add-exports=java.base/jdk.internal.misc=ALL-UNNAMED",
    )
}
tasks.named<JavaExec>("run") {
    // The source launcher encodes each argument so paths and punctuation survive Gradle's command-line parser.
    providers.gradleProperty("turboArgs64").orNull?.let { encoded ->
        args(encoded.split(',').map { String(Base64.getDecoder().decode(it), Charsets.UTF_8) })
    }
    if (System.getProperty("os.name").startsWith("Mac")) jvmArgs("-XstartOnFirstThread")
}
tasks.test {
    useJUnitPlatform()
    jvmArgs(application.applicationDefaultJvmArgs)
}
tasks.register<Jar>("fatJar") {
    group = "build"
    archiveFileName.set("turbo-tides.jar")
    manifest {
        attributes(
            "Main-Class" to application.mainClass.get(),
            // LWJGL supplies its modern Java implementations in multi-release entries.
            "Multi-Release" to "true",
            "Enable-Native-Access" to "ALL-UNNAMED",
            "Add-Exports" to "java.base/jdk.internal.misc",
        )
    }
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
    from(sourceSets.main.get().output)
    dependsOn(configurations.runtimeClasspath)
    from({ configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) } })
    exclude(
        "META-INF/*.SF",
        "META-INF/*.RSA",
        "META-INF/*.DSA",
        "META-INF/INDEX.LIST",
        "module-info.class",
        "META-INF/versions/*/module-info.class",
    )
}
