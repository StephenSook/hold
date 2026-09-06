import type { CapacitorConfig } from '@capacitor/cli'

/**
 * The native shells (PLAN.md task 3.8).
 *
 * The one thing that has to be right here is the API base, and it is not in this file. A native
 * shell loads its own bundle from capacitor:// on iOS and https://localhost on Android, where a
 * relative /api resolves inside the bundle and every request 404s with no useful error. Native
 * builds therefore set VITE_API_BASE to the Cloud Run origin at build time, which the single
 * helper in src/lib/api.ts reads. The server already allows those two origins by name.
 *
 * androidScheme stays https: on http the WebView treats the origin as insecure and refuses the
 * service worker, which would silently remove the offline half of the app on Android only.
 */
const config: CapacitorConfig = {
  appId: 'com.stephensookra.hold',
  appName: 'HOLD',
  webDir: 'dist',
  android: {
    // Release builds are signed from a keystore outside this repository. See PLAN.md task 4.3.
    buildOptions: {
      keystorePath: process.env.HOLD_KEYSTORE_PATH,
      keystoreAlias: process.env.HOLD_KEYSTORE_ALIAS,
    },
  },
  server: {
    androidScheme: 'https',
    iosScheme: 'capacitor',
  },
  ios: {
    contentInset: 'always',
  },
}

export default config
