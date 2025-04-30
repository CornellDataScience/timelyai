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

document.addEventListener("DOMContentLoaded", function () {
    const svg = document.getElementById("perfectPie");
    const breakdownButton = document.getElementById("showBreakdownForm");
    const breakdownModal = document.getElementById("breakdownModal");
    const closeBreakdownButton = document.querySelector(".close-breakdown");
    const submitBreakdownButton = document.getElementById("submitBreakdown");

    // Initial slices
    let slices = [
        { percent: 35, color: "#3CAE63", label: "School" },
        { percent: 25, color: "#FF9800", label: "Clubs" },
        { percent: 20, color: "#2196F3", label: "Friends" },
        { percent: 15, color: "#9C27B0", label: "Hobbies" },
        { percent: 5, color: "#607D8B", label: "Other" },
    ];

    // Draw Pie Chart
    function drawPieChart(sliceData) {
        while (svg.firstChild) {
            svg.removeChild(svg.firstChild);
        }
    
        let startAngle = 0;
    
        sliceData.forEach((slice, index) => {
            let sliceStartAngle = startAngle;
            let sliceEndAngle = startAngle + (slice.percent / 100) * 360;
    
            // Special case if slice is 100% (draw almost a full circle)
            if (slice.percent === 100) {
                sliceEndAngle = sliceStartAngle + 359.999; 
            }
    
            if (slice.percent <= 0) return; // Skip 0% slices
    
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
                svg.querySelectorAll("path").forEach(p => p.style.transform = "scale(1)");
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
                percentText.setAttribute("dominant-baseline", "middle");
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
    

    // First Draw
    drawPieChart(slices);

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
    breakdownButton.addEventListener("click", function () {
        breakdownModal.style.display = "block";
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
    submitBreakdownButton.addEventListener("click", function () {
        slices = [
            { percent: parseFloat(document.getElementById("schoolPercent").value) || 0, color: "#3CAE63", label: "School" },
            { percent: parseFloat(document.getElementById("clubsPercent").value) || 0, color: "#FF9800", label: "Clubs" },
            { percent: parseFloat(document.getElementById("friendsPercent").value) || 0, color: "#2196F3", label: "Friends" },
            { percent: parseFloat(document.getElementById("hobbiesPercent").value) || 0, color: "#9C27B0", label: "Hobbies" },
            { percent: parseFloat(document.getElementById("otherPercent").value) || 0, color: "#607D8B", label: "Other" },
        ];

        drawPieChart(slices);
        breakdownModal.style.display = "none";

        // Clear inputs
        document.getElementById("schoolPercent").value = "";
        document.getElementById("clubsPercent").value = "";
        document.getElementById("friendsPercent").value = "";
        document.getElementById("hobbiesPercent").value = "";
        document.getElementById("otherPercent").value = "";
    });
});
