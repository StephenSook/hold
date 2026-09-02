# Mobile Shell Rules

Lane: `web/android/`, `web/ios/`, `web/src/native/`, `web/capacitor.config.ts`

## Non-negotiable rules

1. **Gate on `Capacitor.isNativePlatform()` before any native call.** Every native plugin
   call must be inside this gate. The web fallback must work without any native plugin.

2. **Privacy manifest required for iOS.** `NSPrivacyAccessedAPICategoryUserDefaults` must be
   declared. Camera usage string must be present.

3. **No em-dashes.** Colon, comma, period, hyphen.

4. **Tool: IBM-Bob trailer on every Bob-authored commit.**

5. **Stage named paths only.** Never `git add -A`.

6. **Never touch:** `web/src/board/`, `web/src/verdict/`, `web/src/import/`, `web/src/judge/`,
   `api/`, `bench/`, `rules/`.

7. **VITE_API_BASE points to the Cloud Run URL** for all `cap sync` builds. Never hardcode a
   localhost URL in the Capacitor config for a production build.

8. **Keystore at `~/.hold-release.jks`, gitignored.** Never commit the keystore or its
   password. Document the location in PLAN.md Notes only.
