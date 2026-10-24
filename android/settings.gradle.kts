// たぐりの Android アプリ（Google Play に出す。TWA: Trusted Web Activity）。中身は https://app.taguri.workers.dev の画面で、
// このアプリは Chrome でその画面を全画面に開く薄い入れ物（plan-app-release、impl-android-twa）。
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "taguri"
include(":app")
