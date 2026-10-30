package org.maherumar.maherumarpos;

import android.app.Activity;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.PhoneAuthCredential;
import com.google.firebase.auth.PhoneAuthOptions;
import com.google.firebase.auth.PhoneAuthProvider;
import com.google.android.gms.tasks.Task;
import java.util.concurrent.TimeUnit;

public final class FirebaseOtpBridge {
    public interface Callback {
        void onCodeSent(String verificationId);
        void onSignedIn(String uid);
        void onError(String message);
    }

    private static FirebaseAuth auth;

    private FirebaseOtpBridge() {}

    public static synchronized void initialize(Activity activity, String appId, String apiKey, String projectId) {
        FirebaseApp app;
        try {
            app = FirebaseApp.getInstance();
        } catch (IllegalStateException missingDefaultApp) {
            FirebaseOptions options = new FirebaseOptions.Builder()
                    .setApplicationId(appId)
                    .setApiKey(apiKey)
                    .setProjectId(projectId)
                    .build();
            app = FirebaseApp.initializeApp(activity.getApplicationContext(), options);
        }
        auth = FirebaseAuth.getInstance(app);
    }

    private static FirebaseAuth getAuth() {
        if (auth == null) {
            throw new IllegalStateException("Firebase Authentication has not been initialized.");
        }
        return auth;
    }

    public static void sendCode(Activity activity, String phoneNumber, Callback callback) {
        try {
            FirebaseAuth firebaseAuth = getAuth();
            PhoneAuthOptions options = PhoneAuthOptions.newBuilder(firebaseAuth)
                    .setPhoneNumber(phoneNumber)
                    .setTimeout(60L, TimeUnit.SECONDS)
                    .setActivity(activity)
                    .setCallbacks(new PhoneAuthProvider.OnVerificationStateChangedCallbacks() {
                        @Override
                        public void onVerificationCompleted(PhoneAuthCredential credential) {
                            signInWithCredential(activity, firebaseAuth, credential, callback);
                        }

                        @Override
                        public void onVerificationFailed(Exception exception) {
                            callback.onError(safeMessage(exception));
                        }

                        @Override
                        public void onCodeSent(String verificationId,
                                               PhoneAuthProvider.ForceResendingToken token) {
                            callback.onCodeSent(verificationId);
                        }
                    })
                    .build();
            PhoneAuthProvider.verifyPhoneNumber(options);
        } catch (Exception exception) {
            callback.onError(safeMessage(exception));
        }
    }

    public static void verifyCode(String verificationId, String code, Callback callback) {
        try {
            PhoneAuthCredential credential =
                    PhoneAuthProvider.getCredential(verificationId, code);
            signInWithCredential(null, getAuth(), credential, callback);
        } catch (Exception exception) {
            callback.onError(safeMessage(exception));
        }
    }

    private static void signInWithCredential(Activity activity, FirebaseAuth firebaseAuth,
                                             PhoneAuthCredential credential, Callback callback) {
        Task<com.google.firebase.auth.AuthResult> task =
                firebaseAuth.signInWithCredential(credential);
        task.addOnCompleteListener(result -> {
            if (result.isSuccessful() && firebaseAuth.getCurrentUser() != null) {
                callback.onSignedIn(firebaseAuth.getCurrentUser().getUid());
            } else {
                Exception error = result.getException();
                callback.onError(safeMessage(error));
            }
        });
    }

    public static String currentUid() {
        FirebaseAuth firebaseAuth = auth;
        if (firebaseAuth == null || firebaseAuth.getCurrentUser() == null) {
            return "";
        }
        return firebaseAuth.getCurrentUser().getUid();
    }

    public static void signOut() {
        getAuth().signOut();
    }

    private static String safeMessage(Exception exception) {
        if (exception == null || exception.getMessage() == null) {
            return "Phone verification failed. Please try again.";
        }
        String message = exception.getMessage();
        if (message.length() > 220) {
            message = message.substring(0, 220);
        }
        return message;
    }
}
