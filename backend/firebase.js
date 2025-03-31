// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyCvY1agnqbLx7wf4HXPL85TLpzNEdK2uNQ",
  authDomain: "timelyai-ff137.firebaseapp.com",
  projectId: "timelyai-ff137",
  storageBucket: "timelyai-ff137.firebasestorage.app",
  messagingSenderId: "845744253750",
  appId: "1:845744253750:web:66b79658d16d211ef32197",
  measurementId: "G-DDEFL10MJT"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);