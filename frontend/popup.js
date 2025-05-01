console.log("Welcome to TimelyAI!");
console.log("🔧 popup.js loaded");

document.addEventListener("DOMContentLoaded", function () {
    const taskList = document.getElementById("taskList");
    const addTaskButton = document.getElementById("showTaskForm");
    const modal = document.getElementById("taskModal");
    const closeButton = document.querySelector(".close");
    const submitTaskButton = document.getElementById("submitTask");

    const userId = "TestALL"; // You can later make this dynamic

    // load task from firestore
    async function loadTasks() {
        taskList.innerHTML = "<li>Loading tasks...</li>"; // ⏳ loading indicator
        try {
            const response = await fetch(`http://localhost:8888/api/tasks?userId=${userId}`);
            const tasks = await response.json();
    
            taskList.innerHTML = ""; // Clear the list
            
            if (tasks.length === 0) {
                taskList.innerHTML = "<li>No tasks found.</li>";
                return;
            }
    
            tasks.forEach(task => {
                const emoji = getCategoryEmoji(task.category || "Other");
                const li = document.createElement("li");
                
                li.innerHTML = `
                    <strong>${emoji} ${task.title}</strong>
                    <span>Due: ${task.dueDate} | Duration: ${task.duration} | Category: ${task.category}</span>
                `;
                
                li.style.cursor = "pointer"; 

                // ✅ Add click listener to show modal
                li.addEventListener("click", () => {
                    document.getElementById("taskModalTitle").textContent = task.title;
                    document.getElementById("taskModalDue").textContent = task.dueDate;
                    document.getElementById("taskModalDuration").textContent = task.duration;
                    document.getElementById("taskModalCategory").textContent = task.category;
            
                    document.getElementById("taskDetailModal").style.display = "block";
                });
            
                taskList.appendChild(li);
            });
            
            console.log("✅ Tasks refreshed from backend.");
        } catch (err) {
            console.error("❌ Failed to fetch tasks:", err);
            taskList.innerHTML = "<li>Error loading tasks.</li>";
        }
    }
        // Close button
    document.getElementById("closeTaskDetailModal").addEventListener("click", () => {
        document.getElementById("taskDetailModal").style.display = "none";
    });

    // Close when clicking outside modal
    window.addEventListener("click", (event) => {
        const modal = document.getElementById("taskDetailModal");
        if (event.target === modal) {
            modal.style.display = "none";
        }
    });


    // 🚀 Initial task load
    loadTasks();

    // 🎯 Modal logic
    addTaskButton.addEventListener("click", () => modal.style.display = "block");
    closeButton.addEventListener("click", () => modal.style.display = "none");
    window.addEventListener("click", event => {
        if (event.target === modal) modal.style.display = "none";
    });

    // 📝 Submit a new task
    submitTaskButton.addEventListener("click", () => {
        let title = document.getElementById("taskTitle").value.trim() || "Untitled Task";
        let dueDate = document.getElementById("taskDueDate").value;
        let duration = document.getElementById("taskDuration").value.trim() || "TBD";
        let category = document.getElementById("taskCategory").value.trim() || "None";

        if (dueDate) {
            const [year, month, day] = dueDate.split("-");
            dueDate = `${parseInt(month)}/${parseInt(day)}/${year.slice(-2)}`;
        } else {
            dueDate = "TBD";
        }

        const taskDetails = { title, dueDate, duration, category };

        fetch('http://localhost:8888/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId, taskDetails })
        })
        .then(res => res.json())
        .then(data => {
            console.log('✅ Task added:', data);
            loadTasks(); // 🔄 Refresh task list
        })
        .catch(error => {
            console.error('❌ Error sending task:', error);
        });

        // Reset modal form and close
        modal.style.display = "none";
        document.getElementById("taskTitle").value = "";
        document.getElementById("taskDueDate").value = "";
        document.getElementById("taskDuration").value = "";
        document.getElementById("taskCategory").value = "School";
    });

    // 📅 Simple event creation alert
    document.getElementById("createEvent").addEventListener("click", function () {
        const title = document.getElementById("eventTitle").value;
        const date = document.getElementById("eventDate").value;
        const time = document.getElementById("eventTime").value;
        const location = document.getElementById("eventLocation").value;

        if (title && date && time && location) {
            alert(`Event Created: ${title} on ${date} at ${time} in ${location}`);
        } else {
            alert("Please fill out all fields!");
        }
    });
});

// 🎨 Emoji utility
function getCategoryEmoji(category) {
    switch (category) {
        case "School": return "📚";
        case "Clubs": return "🏀";
        case "Friends": return "👯‍♀️";
        case "Hobbies": return "🎨";
        case "Other": return "💪";
        default: return "✅";
    }
}

function renderEvents(events) {
    const eventListEl = document.getElementById("eventList");
  
    eventListEl.innerHTML = "";
  
    if (Object.keys(events).length === 0) {
      eventListEl.innerHTML = "<li>No events found.</li>";
      return;
    }
  
    for (const [id, e] of Object.entries(events)) {
      const li = document.createElement("li");
      li.innerHTML = `
        <strong>${e.summary || e.title}</strong>
        <span>${e.start_time ? new Date(e.start_time).toLocaleString() : ""}</span>
        <span>${e.location || ""}</span>
      `;
  
      // ✅ Show event modal on click
      li.addEventListener("click", () => {
        document.getElementById("eventModalTitle").textContent = e.summary || e.title;
        document.getElementById("eventModalTime").textContent = new Date(e.start_time).toLocaleString();
        document.getElementById("eventModalLocation").textContent = e.location || "Not specified";
  
        document.getElementById("eventModal").style.display = "block";
      });
  
      eventListEl.appendChild(li);
    }
  
    // 🔁 Modal close behavior
    document.getElementById("closeEventModal").addEventListener("click", () => {
      document.getElementById("eventModal").style.display = "none";
    });
  
    window.addEventListener("click", (event) => {
      if (event.target === document.getElementById("eventModal")) {
        document.getElementById("eventModal").style.display = "none";
      }
    });
  }