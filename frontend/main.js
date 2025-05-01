// main.js

document.addEventListener("DOMContentLoaded", function () {
    const tabButtons = document.querySelectorAll(".tablinks");
    const sections = document.querySelectorAll(".section");
  
    tabButtons.forEach((button) => {
      button.addEventListener("click", function () {
        const targetPanel = this.getAttribute("data-panel");
  
        // Hide all sections
        sections.forEach((section) => {
          section.style.display = "none";
        });
  
        // Remove 'active' class from all buttons
        tabButtons.forEach((btn) => {
          btn.classList.remove("active");
        });
  
        // Show the target section
        document.getElementById(targetPanel).style.display = "block";
        this.classList.add("active");
      });
    });
  
    // Optionally show the first section on load
    tabButtons[0].click();
  });
  