plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.hilt)
}

android {
    namespace = "com.minimoney.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.minimoney.app"
        minSdk = 24
        targetSdk = 35
        versionCode = 10
        versionName = "0.10.0"

        // Backend: Supabase Edge Functions (see supabase/README.md).
        buildConfigField("String", "API_BASE_URL", "\"https://iftunypqqptuzoscuiub.supabase.co/functions/v1/\"")

        // Google OAuth Web Client ID — the audience for Credential Manager's
        // Google Sign-In ID tokens (verified server-side in auth-google).
        buildConfigField("String", "GOOGLE_WEB_CLIENT_ID", "\"148178496329-keig9g4apiorhsng4firv1ps84436jn8.apps.googleusercontent.com\"")

        // Pilot stage: late-penalty cap is 3 Mbucks (vs 7 in production).
        // Flip to false only at the wider-release milestone.
        buildConfigField("boolean", "IS_PILOT", "true")
    }

    buildTypes {
        debug {
            // LOCKED CONSTRAINT: never add applicationIdSuffix here
            // (Android 16 process freeze on Samsung Galaxy S22 Ultra).
        }
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    // Versioned Room schema snapshots, committed for migration verification.
    ksp {
        arg("room.schemaLocation", "$projectDir/schemas")
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

// BuildSpec §Compliance terminology governance: debt-coded language is reserved
// to parent-facing surfaces. This check fails the build if such a term appears
// in any child-facing string resource file (strings_child*.xml).
val childFacingTermLint = tasks.register("childFacingTermLint") {
    val resDir = layout.projectDirectory.dir("src/main/res")
    val forbiddenTerms = listOf("invoice", "arrears", "penalty", "debt", "overdue", "fine", "late fee")
    inputs.dir(resDir)
    doLast {
        resDir.asFileTree.matching { include("**/strings_child*.xml") }.forEach { file ->
            // Strip XML comments — only renderable string content can reach a child's screen.
            val text = file.readText().replace(Regex("<!--.*?-->", RegexOption.DOT_MATCHES_ALL), "").lowercase()
            forbiddenTerms.forEach { term ->
                check(!text.contains(term)) {
                    "Debt-coded term \"$term\" found in child-facing resource ${file.name} " +
                        "(BuildSpec §Compliance: terminology governance)"
                }
            }
        }
    }
}
tasks.named("preBuild") { dependsOn(childFacingTermLint) }

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui.tooling.preview)
    debugImplementation(libs.androidx.compose.ui.tooling)

    implementation(libs.hilt.android)
    implementation(libs.hilt.navigation.compose)
    implementation(libs.navigation.compose)
    ksp(libs.hilt.compiler)

    implementation(libs.retrofit)
    implementation(libs.retrofit.kotlinx.serialization)
    implementation(libs.okhttp)
    debugImplementation(libs.okhttp.logging)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.core)

    implementation(libs.androidx.datastore.preferences)

    implementation(libs.work.runtime.ktx)
    implementation(libs.hilt.work)
    ksp(libs.androidx.hilt.compiler)

    implementation(libs.androidx.room.runtime)
    implementation(libs.androidx.room.ktx)
    ksp(libs.androidx.room.compiler)

    implementation(libs.androidx.credentials)
    implementation(libs.androidx.credentials.play.services.auth)
    implementation(libs.googleid)

    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.turbine)
    testImplementation(libs.mockk)
}
