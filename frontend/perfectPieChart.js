function polarToCartesian(cx, cy, r, angleDeg) {
    const rad = (angleDeg - 90) * Math.PI / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArcPath(cx, cy, r, startAngle, endAngle) {
    const start = polarToCartesian(cx, cy, r, startAngle);
    const end = polarToCartesian(cx, cy, r, endAngle);
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y} Z`;
}

// Draw Pie Chart
export function drawPieChart(sliceData, svg, savedGoals = {}) {
    while (svg.firstChild) {
        svg.removeChild(svg.firstChild);
    }

    let startAngle = 0;

    sliceData.forEach((slice) => {
        let sliceStartAngle = startAngle;
        let sliceEndAngle = sliceStartAngle + (slice.percent / 100) * 360;

        if (slice.percent === 100) sliceEndAngle = sliceStartAngle + 359.999;
        if (slice.percent <= 0) return;

        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", describeArcPath(150, 150, 140, sliceStartAngle, sliceEndAngle));
        path.setAttribute("fill", slice.color);
        path.style.transition = "transform 0.3s, filter 0.3s";

        path.addEventListener("mouseover", () => {
            path.style.transform = "scale(1.05)";
            path.style.transformOrigin = "150px 150px";
            path.style.filter = "brightness(1.2) drop-shadow(0 0 6px rgba(0,0,0,0.2))";
        });
        path.addEventListener("mouseout", () => {
            path.style.transform = "scale(1)";
            path.style.filter = "none";
        });

        path.addEventListener("click", () => {
            svg.querySelectorAll("path").forEach((p) => p.style.transform = "scale(1)");
            path.style.transform = "scale(1.08)";
            const oldGroup = document.getElementById("center-info-group");
            if (oldGroup) oldGroup.remove();

            const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
            group.setAttribute("id", "center-info-group");
            group.style.opacity = "0";
            group.style.transition = "opacity 0.6s ease, transform 0.6s ease";
            group.setAttribute("transform", "scale(0.9)");

            const percentText = document.createElementNS("http://www.w3.org/2000/svg", "text");
            percentText.setAttribute("x", "150");
            percentText.setAttribute("y", "140");
            percentText.setAttribute("text-anchor", "middle");
            percentText.setAttribute("font-size", "34");
            percentText.setAttribute("font-weight", "bold");
            percentText.setAttribute("fill", slice.color);
            percentText.style.filter = `
                    drop-shadow(0px 0px 8px ${slice.color}44) 
                    drop-shadow(0px 0px 6px rgba(0,0,0,0.03))
            `;
            percentText.style.opacity = "0.96";
            percentText.textContent = `${slice.percent}%`;

            const labelText = document.createElementNS("http://www.w3.org/2000/svg", "text");
            labelText.setAttribute("x", "150");
            labelText.setAttribute("y", "170");
            labelText.setAttribute("text-anchor", "middle");
            labelText.setAttribute("font-size", "18");
            labelText.setAttribute("font-weight", "600");
            labelText.setAttribute("fill", slice.color);
            labelText.style.filter = `
                    drop-shadow(0px 0px 4px ${slice.color}33) 
                    drop-shadow(0px 0px 5px rgba(0,0,0,0.02))
            `;
            labelText.style.opacity = "0.94";
            labelText.textContent = slice.label;

            group.appendChild(percentText);
            group.appendChild(labelText);
            const goalPercent = savedGoals[slice.label];

            if (goalPercent !== undefined) {
                const goalText = document.createElementNS("http://www.w3.org/2000/svg", "text");
                goalText.setAttribute("x", "150");
                goalText.setAttribute("y", "190"); // slightly below labelText
                goalText.setAttribute("text-anchor", "middle");
                goalText.setAttribute("font-size", "14");
                goalText.setAttribute("fill", "#555");
                goalText.style.opacity = "0.85";
                goalText.textContent = `Goal: ${goalPercent}%`;
                group.appendChild(goalText);
            }

            svg.appendChild(group);

            setTimeout(() => {
                group.style.opacity = "1";
                group.setAttribute("transform", "scale(1)");
            }, 10);
        });

        svg.appendChild(path);
        startAngle = sliceEndAngle;
    });

    const centerHole = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    centerHole.setAttribute("cx", "150");
    centerHole.setAttribute("cy", "150");
    centerHole.setAttribute("r", "70");
    centerHole.setAttribute("fill", "#ffffff");
    centerHole.style.filter = "drop-shadow(0 0 6px rgba(0,0,0,0.05))";
    svg.appendChild(centerHole);
}

async function loadGoals() {
    try {
        const res = await fetch("http://localhost:8888/api/goals?userId=TestALL");
        const data = await res.json();

        if (data.goals && typeof data.goals === 'object') {
            const colorMap = {
                "School": "#3CAE63",
                "Clubs": "#FF9800",
                "Friends": "#2196F3",
                "Hobbies": "#9C27B0",
                "Other": "#607D8B"
            };

            slices = Object.entries(data.goals).map(([label, percent]) => ({
                label,
                percent,
                color: colorMap[label] || "#999999"
            }));

            drawPieChart(slices, svg, data.goals);
            console.log("✅ Loaded goals from backend");
        } else {
            console.log("⚠️ No saved goals found. Using defaults.");
        }
    } catch (err) {
        console.error("❌ Error loading goals from backend:", err);
    }
}

async function loadTasksAndRedraw() {
    const svg = document.getElementById("perfectPie");

    const response = await fetch(`http://localhost:8888/api/tasks?userId=TestALL`);
    const tasks = await response.json();

    let weeklyBreakup = { School: 0, Clubs: 0, Friends: 0, Hobbies: 0, Other: 0 };
    tasks.forEach(task => {
        if (!isNaN(task.duration) && task.duration.trim() !== "") {
            weeklyBreakup[task.category] += parseInt(task.duration);
        }
    });

    const total = Object.values(weeklyBreakup).reduce((a, b) => a + b, 0);
    const colorMap = {
        School: "#3CAE63",
        Clubs: "#FF9800",
        Friends: "#2196F3",
        Hobbies: "#9C27B0",
        Other: "#607D8B",
    };

    const slices = Object.entries(weeklyBreakup).map(([label, count]) => ({
        label,
        percent: total === 0 ? 0 : parseFloat(((count / total) * 100).toFixed(1)),
        color: colorMap[label] || "#999"
    }));

    // ⬇️ Fetch latest goals
    const goalsRes = await fetch("http://localhost:8888/api/goals?userId=TestALL");
    const { goals = {} } = await goalsRes.json();

    drawPieChart(slices, svg, goals);
}

document.addEventListener("DOMContentLoaded", function () {
    const svg = document.getElementById("perfectPie");
    const breakdownButton = document.getElementById("showBreakdownForm");
    const breakdownModal = document.getElementById("breakdownModal");
    const closeBreakdownButton = document.querySelector(".close-breakdown");
    const submitBreakdownButton = document.getElementById("submitBreakdown");

    // First Draw
    loadGoals();

    // Click outside pie chart = remove center info
    svg.addEventListener("click", function (e) {
        if (e.target.tagName !== "path") {
            svg.querySelectorAll("path").forEach(p => p.style.transform = "scale(1)");
            const oldGroup = document.getElementById("center-info-group");
            if (oldGroup) {
                oldGroup.style.opacity = "0";
                oldGroup.style.transform = "scale(0.8)";
                setTimeout(() => oldGroup.remove(), 400);
            }
        }
    });

    // Modal control
    breakdownButton.addEventListener("click", async function () {
        breakdownModal.style.display = "block";
    
        try {
            const res = await fetch("http://localhost:8888/api/goals?userId=TestALL");
            const data = await res.json();
    
            if (data.goals) {
                document.getElementById("schoolPercent").value = data.goals["School"] || "";
                document.getElementById("clubsPercent").value = data.goals["Clubs"] || "";
                document.getElementById("friendsPercent").value = data.goals["Friends"] || "";
                document.getElementById("hobbiesPercent").value = data.goals["Hobbies"] || "";
                document.getElementById("otherPercent").value = data.goals["Other"] || "";
            }
        } catch (err) {
            console.error("❌ Failed to load saved goals:", err);
        }
    });
    

    closeBreakdownButton.addEventListener("click", function () {
        breakdownModal.style.display = "none";
    });

    window.addEventListener("click", function (event) {
        if (event.target === breakdownModal) {
            breakdownModal.style.display = "none";
        }
    });

    // Update slices
    submitBreakdownButton.addEventListener("click", async function () {
    
        breakdownModal.style.display = "none";
        // Save to Firebase
        // Save to Firebase
        try {
            const goals = {
                School: parseFloat(document.getElementById("schoolPercent").value) || 0,
                Clubs: parseFloat(document.getElementById("clubsPercent").value) || 0,
                Friends: parseFloat(document.getElementById("friendsPercent").value) || 0,
                Hobbies: parseFloat(document.getElementById("hobbiesPercent").value) || 0,
                Other: parseFloat(document.getElementById("otherPercent").value) || 0,
            };

            await fetch("http://localhost:8888/api/goals", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    userId: "TestALL",
                    goals: goals
                })
            });

            console.log("✅ Goals saved to backend!");
        } catch (error) {
            console.error("❌ Failed to save goals:", error);
        }

        await loadTasksAndRedraw();

        breakdownModal.style.display = "none";
    });    
});
