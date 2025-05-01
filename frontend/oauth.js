// function handleLogin() {
//     chrome.identity.getAuthToken({ interactive: false }, function(existingToken) {
//       if (existingToken) {
//         chrome.identity.removeCachedAuthToken({ token: existingToken }, function() {
//           getNewToken();
//         });
//       } else {
//         getNewToken();
//       }
//     });
  
//     function getNewToken() {
//       chrome.identity.getAuthToken({ interactive: true }, function(newToken) {
//         if (chrome.runtime.lastError) {
//           console.error("Auth error:", chrome.runtime.lastError.message);
//           alert("Login failed: " + chrome.runtime.lastError.message);
//           return;
//         }
  
//         console.log("New OAuth token:", newToken);
  
//         fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
//           method: "GET",
//           headers: {
//             "Authorization": "Bearer " + newToken
//           }
//         })
//         .then(response => response.json())
//         .then(userInfo => {
//           console.log("User info:", userInfo);
//           if (userInfo.email) {
//             chrome.storage.local.set({
//               userEmail: userInfo.email,
//               authToken: newToken
//             }, () => {
//               // 👇 Change default popup to index.html
//               chrome.action.setPopup({ popup: "index.html" }, () => {
//                 // Optionally reload the popup to reflect the change
//                 window.location.href = "index.html";
//               });
//             });
//           } else {
//             alert("Logged in, but no email retrieved.");
//           }
//         })
//         .catch(err => {
//           console.error("Failed to fetch user info:", err);
//           alert("Failed to fetch user info.");
//         });
//       });
//     }
//   }
  
//   document.addEventListener('DOMContentLoaded', () => {
//     const loginBtn = document.getElementById('loginBtn');
//     if (loginBtn) {
//       loginBtn.addEventListener('click', handleLogin);
//     }
//   });
// function handleLogin() {
//   // Skip token caching logic — go straight to interactive auth
//   console.log("🔐 Requesting OAuth token...");
//   chrome.identity.getAuthToken({ interactive: true }, function(newToken) {
//     if (chrome.runtime.lastError) {
//       console.error("Auth error:", chrome.runtime.lastError.message);
//       alert("Login failed: " + chrome.runtime.lastError.message);
//       return;
//     }

//     console.log("✅ New OAuth token:", newToken);

//     // Fetch user info
//     fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
//       method: "GET",
//       headers: {
//         "Authorization": "Bearer " + newToken
//       }
//     })
//     .then(response => response.json())
//     .then(userInfo => {
//       console.log("✅ User info:", userInfo);
//       if (userInfo.email) {
//         const userId = userInfo.email
//         // Step 1: Initialize user document if needed
//         fetch("http://localhost:8888/api/init-user", {
//           method: "POST",
//           headers: {
//             "Content-Type": "application/json"
//           },
//           body: JSON.stringify({ userId: userId })
//         })
//         .then(initRes => initRes.json())
//         .then(initData => {
//           console.log("🛠️ User initialization status:", initData.status);

//           // Step 2: Save credentials and redirect
//           chrome.storage.local.set({
//             userEmail: userId,
//             authToken: newToken
//           }, () => {
//             chrome.action.setPopup({ popup: "index.html" }, () => {
//               window.location.href = "index.html";
//             });
//           });
//         })
//         .catch(err => {
//           console.error("❌ Failed to initialize user doc:", err);
//           alert("Login succeeded, but we couldn't set up your account.");
//         });
//         chrome.storage.local.set({
//           userEmail: userInfo.email,
//           authToken: newToken
//         }, () => {
//           chrome.action.setPopup({ popup: "index.html" }, () => {
//             window.location.href = "index.html";
//           });
//         });
//       } else {
//         alert("Logged in, but no email retrieved.");
//       }
//     })
//     .catch(err => {
//       console.error("❌ Failed to fetch user info:", err);
//       alert("❌ Error retrieving account info.");
//     });
//   });
// }
function handleLogin() {
  console.log("🔐 Starting login flow...");

  chrome.identity.getAuthToken({ interactive: true }, function(newToken) {
    if (chrome.runtime.lastError) {
      console.error("❌ Auth error:", chrome.runtime.lastError.message);
      alert("Login failed: " + chrome.runtime.lastError.message);
      return;
    }

    console.log("✅ OAuth token received:", newToken);

    // Step 1: Fetch user info from Google
    fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
      method: "GET",
      headers: {
        "Authorization": "Bearer " + newToken
      }
    })
    .then(response => {
      console.log("🌐 Fetched user info response status:", response.status);
      return response.json();
    })
    .then(userInfo => {
      console.log("👤 Parsed user info:", userInfo);

      if (userInfo.email) {
        const userId = userInfo.email;
        console.log("📧 Using user email as ID:", userId);
        
        // Step 2: Initialize user document in backend
        fetch("http://localhost:8888/api/init-user", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ userId })
        })
        .then(async initRes => {
          console.log("📡 Backend responded with status:", initRes.status);
        
          let initData;
          try {
            initData = await initRes.json(); // may throw!
            console.log("🛠️ User initialization result:", initData);
          } catch (e) {
            console.error("❌ Failed to parse JSON from init-user:", e);
            alert("Something went wrong setting up your account. Please try again.");
            return;
          }
        
          // Optional: check if backend returned an error object
          if (initData.status === "error") {
            alert("Backend failed: " + (initData.message || "Unknown error"));
            return;
          }
        
          // Step 3: Save credentials and redirect
          chrome.storage.local.set({
            userEmail: userId,
            authToken: newToken
          }, () => {
            console.log("💾 Credentials saved to chrome.storage");
        
            chrome.action.setPopup({ popup: "index.html" }, () => {
              console.log("🔁 Popup set to index.html — redirecting...");
              window.location.href = "index.html";  // This should now work
              try {
                window.location.href = "index.html";
              } catch (redirectErr) {
                console.error("❌ Redirect failed:", redirectErr);
                alert("Login completed but we couldn't open the main page.");
              }
            });
          });
        })
        .catch(err => {
          console.error("❌ Backend init-user fetch error:", err);
          alert("Login succeeded, but we couldn't reach the backend.");
        });
        

      } else {
        alert("Logged in, but no email retrieved.");
        console.warn("⚠️ userInfo.email was undefined:", userInfo);
      }
    })
    .catch(err => {
      console.error("❌ Failed to fetch user info:", err);
      alert("❌ Error retrieving account info.");
    });
  });
}

// Bind login button
document.addEventListener('DOMContentLoaded', () => {
  const loginBtn = document.getElementById('loginBtn');
  if (loginBtn) {
    loginBtn.addEventListener('click', handleLogin);
  }
});
