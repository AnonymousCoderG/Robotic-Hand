// This script runs in the background (a separate thread)

// Import the main MediaPipe Hands library
importScripts('https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js');

// --- THIS IS THE CRITICAL FIX ---
// We must explicitly tell the Hands instance where to find its model and data files.
const hands = new Hands({
    locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
    }
});
// --------------------------------

hands.setOptions({
    maxNumHands: 1,
    modelComplexity: 0, // Use the fastest model
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5
});

// When the main thread sends a message (an image frame), process it
self.onmessage = (event) => {
    // We expect an ImageBitmap for best performance
    const imageBitmap = event.data;
    hands.send({ image: imageBitmap });
};

// When MediaPipe has results, send them back to the main thread
hands.onResults((results) => {
    // Post the landmarks and the processed image back
    self.postMessage({ landmarks: results.multiHandLandmarks, image: results.image });
});