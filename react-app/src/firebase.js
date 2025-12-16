import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getAnalytics } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyCB2BfnRlaPkfdPQVKd_mJbQPa2eVPG_is",
  authDomain: "restaureantf.firebaseapp.com",
  projectId: "restaureantf",
  storageBucket: "restaureantf.firebasestorage.app",
  messagingSenderId: "387903781362",
  appId: "1:387903781362:web:daaeabbb3387e34791936b",
  measurementId: "G-3CT4CWFR83"
};

const app = initializeApp(firebaseConfig);

// Initialize Analytics (only in browser environment)
let analytics = null;
if (typeof window !== 'undefined') {
  analytics = getAnalytics(app);
}

// Initialize Auth
const auth = getAuth(app);

export { app, auth, analytics };
