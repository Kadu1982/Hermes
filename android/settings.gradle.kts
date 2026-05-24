pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "Hermes"
include(":app")
include(":core:network")
include(":core:security")
include(":feature:pairing")
include(":feature:status")
include(":feature:commands")
include(":feature:inventory")
include(":feature:files")
