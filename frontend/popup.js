console.log("Welcome to TimelyAI!");

// Task Management
document.addEventListener("DOMContentLoaded", function () {
    const taskList = document.getElementById("taskList");
    const addTaskButton = document.getElementById("showTaskForm"); // Button that shows the modal
    const modal = document.getElementById("taskModal");
    const closeButton = document.querySelector(".close");
    const submitTaskButton = document.getElementById("submitTask");

    // Open modal when clicking "Add Task"
    addTaskButton.addEventListener("click", function () {
        modal.style.display = "block";
    });

    // Close modal when clicking "X"
    closeButton.addEventListener("click", function () {
        modal.style.display = "none";
    });

    // Close modal when clicking outside of it
    window.addEventListener("click", function (event) {
        if (event.target === modal) {
            modal.style.display = "none";
        }
    });

    // Submit task when clicking "Add Task"
    submitTaskButton.addEventListener("click", function () {
        let title = document.getElementById("taskTitle").value.trim() || "Untitled Task";
        let dueDate = document.getElementById("taskDueDate").value;
        if (dueDate) {
            const dueDateItems = dueDate.split("-");
            let monthItem = dueDateItems[1];
            let dayItem = dueDateItems[2];

            // Remove leading zeros by converting to integer
            monthItem = parseInt(monthItem).toString();
            dayItem = parseInt(dayItem).toString();

            dueDate = `${monthItem}/${dayItem}/${dueDateItems[0].slice(-2)}`;
        } else {
            dueDate = "TBD";
        }
        let duration = document.getElementById("taskDuration").value.trim() || "TBD";
        let category = document.getElementById("taskCategory").value.trim() || "None";
        
        let emoji = "✅";
        
        if (category == "School") {
            emoji = "📚";
        }
        if (category == "Clubs") {
            emoji = "🏀";
        }
        if (category == "Friends") {
            emoji = "👯‍♀️";
        }
        if (category == "Hobbies") {
            emoji = "🎨";
        }
        if (category == "Other") {
            emoji = "💪";
        }
        
        if (title !== "Untitled Task") {
            let li = document.createElement("li");
            li.innerHTML = `
                <strong>${emoji} ${title}</strong>
                <span>Due: ${dueDate} | Duration: ${duration} | Category: ${category}</span>
            `;
            taskList.appendChild(li);
        }

        // Send task to backend 
        const taskDetails = {
            title,
            dueDate,
            duration,
            category
        };
        
        fetch('http://localhost:4000/api/tasks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                userId: "TestALL",
                taskDetails: taskDetails
            })
        })
        .then(res => res.json())
        .then(data => {
            console.log('✅ Task sent to backend:', data);
        })
        .catch(error => {
            console.error('❌ Error sending task:', error);
        });

        // Close the modal
        modal.style.display = "none";

        // Clear input fields
        document.getElementById("taskTitle").value = "";
        document.getElementById("taskDueDate").value = "";
        document.getElementById("taskDuration").value = "";
        document.getElementById("taskCategory").value = "School";

    });

    // Event Creation
    document.getElementById("createEvent").addEventListener("click", function () {
        let title = document.getElementById("eventTitle").value;
        let date = document.getElementById("eventDate").value;
        let time = document.getElementById("eventTime").value;
        let location = document.getElementById("eventLocation").value;

        if (title && date && time && location) {
            alert(`Event Created: ${title} on ${date} at ${time} in ${location}`);
        } else {
            alert("Please fill out all fields!");
        }
    });
});
