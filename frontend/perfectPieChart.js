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
    const slices = [
        { percent: 35, color: "#3CAE63", label: "School" },
        { percent: 25, color: "#FF9800", label: "Clubs" },
        { percent: 20, color: "#2196F3", label: "Friends" },
        { percent: 15, color: "#9C27B0", label: "Hobbies" },
        { percent: 5, color: "#607D8B", label: "Other" },
    ];

    const svg = document.getElementById("perfectPie");
    let startAngle = 0;

    // Draw pie slices
    slices.forEach((slice, index) => {
        const sliceStartAngle = startAngle;
        const sliceEndAngle = startAngle + (slice.percent / 100) * 360;

        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", describeArcPath(150, 150, 140, sliceStartAngle, sliceEndAngle));
        path.setAttribute("fill", slice.color);
        path.style.transition = "transform 0.3s, filter 0.3s";

        // Hover pop effect
        path.addEventListener("mouseover", () => {
            path.style.transform = "scale(1.05)";
            path.style.transformOrigin = "150px 150px";
            path.style.filter = "brightness(1.2) drop-shadow(0 0 6px rgba(0,0,0,0.2))";
        });
        path.addEventListener("mouseout", () => {
            path.style.transform = "scale(1)";
            path.style.filter = "none";
        });

        // Click: show fancy center text inside the donut hole
        path.addEventListener("click", () => {
            svg.querySelectorAll("path").forEach(p => p.style.transform = "scale(1)");
            path.style.transform = "scale(1.08)";
        
            const oldGroup = document.getElementById("center-info-group");
            if (oldGroup) oldGroup.remove();
        
            // Gradient setup
            const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
            const gradient = document.createElementNS("http://www.w3.org/2000/svg", "linearGradient");
            gradient.setAttribute("id", `textGradient${index}`);
            gradient.setAttribute("x1", "0%");
            gradient.setAttribute("y1", "0%");
            gradient.setAttribute("x2", "0%");
            gradient.setAttribute("y2", "100%");
            const stop1 = document.createElementNS("http://www.w3.org/2000/svg", "stop");
            stop1.setAttribute("offset", "0%");
            stop1.setAttribute("stop-color", slice.color);
            const stop2 = document.createElementNS("http://www.w3.org/2000/svg", "stop");
            stop2.setAttribute("offset", "100%");
            stop2.setAttribute("stop-color", "#ffffff");
            gradient.appendChild(stop1);
            gradient.appendChild(stop2);
            defs.appendChild(gradient);
            svg.appendChild(defs);
        
            // Group for text
            const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
            group.setAttribute("id", "center-info-group");
            group.style.opacity = "0";
            group.style.transition = "opacity 0.6s ease, transform 0.6s ease";
            group.setAttribute("transform", "scale(0.9)");
        
            // Percentage text - larger and vertically centered
            const percentText = document.createElementNS("http://www.w3.org/2000/svg", "text");
            percentText.setAttribute("x", "150");
            percentText.setAttribute("y", "140");  // Slightly higher
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
        
            // Label below with good spacing and same glow tone
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

    // Add hollow center circle (donut effect)
    const centerHole = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    centerHole.setAttribute("cx", "150");
    centerHole.setAttribute("cy", "150");
    centerHole.setAttribute("r", "70");
    centerHole.setAttribute("fill", "#ffffff");
    centerHole.style.filter = "drop-shadow(0 0 6px rgba(0,0,0,0.05))";
    svg.appendChild(centerHole);

    // Click outside: remove text and reset
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
});
