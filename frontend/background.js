chrome.action.onClicked.addListener(async () => {
    const userId = "user123"; // You can dynamically fetch this later
    const url = `http://localhost:8888/api/tasks?userId=${userId}`; // Adjust if deployed
  
    try {
      const response = await fetch(url);
      const tasks = await response.json();
      console.log("Fetched tasks:", tasks);
  
      // Save tasks for popup.js to read
      chrome.storage.local.set({ tasks });
    } catch (err) {
      console.error("Error fetching tasks:", err);
    }
  });
  