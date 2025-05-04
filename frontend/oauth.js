function handleLogin() {
    chrome.identity.getAuthToken({ interactive: false }, function(existingToken) {
      if (existingToken) {
        chrome.identity.removeCachedAuthToken({ token: existingToken }, function() {
          getNewToken();
        });
      } else {
        getNewToken();
      }
    });
  
    function getNewToken() {
      chrome.identity.getAuthToken({ interactive: true }, function(newToken) {
        if (chrome.runtime.lastError) {
          console.error("Auth error:", chrome.runtime.lastError.message);
          alert("Login failed: " + chrome.runtime.lastError.message);
          return;
        }
  
        console.log("New OAuth token:", newToken);
  
        fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
          method: "GET",
          headers: {
            "Authorization": "Bearer " + newToken
          }
        })
        .then(response => response.json())
        .then(userInfo => {
          console.log("User info:", userInfo);
          if (userInfo.email) {
            chrome.storage.local.set({
              userEmail: userInfo.email,
              authToken: newToken
            }, () => {
              // 👇 Change default popup to index.html
              chrome.action.setPopup({ popup: "index.html" }, () => {
                // Optionally reload the popup to reflect the change
                window.location.href = "index.html";
              });
            });
          } else {
            alert("Logged in, but no email retrieved.");
          }
        })
        .catch(err => {
          console.error("Failed to fetch user info:", err);
          alert("Failed to fetch user info.");
        });
      });
    }
  }
  
  document.addEventListener('DOMContentLoaded', () => {
    const loginBtn = document.getElementById('loginBtn');
    if (loginBtn) {
      loginBtn.addEventListener('click', handleLogin);
    }
  });
  