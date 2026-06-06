import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteStaticCopy } from 'vite-plugin-static-copy'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({
      targets: [
        // Silero VAD model files
        {
          src: 'node_modules/@ricky0123/vad-web/dist/silero_vad_legacy.onnx',
          dest: 'vad',
        },
        {
          src: 'node_modules/@ricky0123/vad-web/dist/silero_vad_v5.onnx',
          dest: 'vad',
        },
        // VAD AudioWorklet script
        {
          src: 'node_modules/@ricky0123/vad-web/dist/vad.worklet.bundle.min.js',
          dest: 'vad',
        },
        // ONNX Runtime WASM files (required by Silero VAD)
        {
          src: 'node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.mjs',
          dest: 'vad',
        },
        {
          src: 'node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.wasm',
          dest: 'vad',
        },
      ],
    }),
  ],
})
