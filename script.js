document.addEventListener("DOMContentLoaded", () => {
    // 1. Initial page load animations using native Web Animations API
    document.querySelectorAll(".motion-element").forEach((el, index) => {
        el.animate([
            { opacity: 0, transform: 'translateY(30px)' },
            { opacity: 1, transform: 'translateY(0)' }
        ], {
            duration: 800,
            delay: index * 150,
            fill: 'forwards',
            easing: 'ease-out'
        });
    });

    let mockLogs = [
        { name: "Sarah Connor", time: "09:05 AM", role: "Developer", img: "https://ui-avatars.com/api/?name=Sarah+Connor&background=10B981&color=fff&bold=true", color: "10B981" },
        { name: "John Smith", time: "08:58 AM", role: "Designer", img: "https://ui-avatars.com/api/?name=John+Smith&background=3B82F6&color=fff&bold=true", color: "3B82F6" },
        { name: "Emily Chen", time: "08:45 AM", role: "HR Manager", img: "https://ui-avatars.com/api/?name=Emily+Chen&background=8B5CF6&color=fff&bold=true", color: "8B5CF6" },
        { name: "Michael Doe", time: "08:30 AM", role: "Marketing", img: "https://ui-avatars.com/api/?name=Michael+Doe&background=F59E0B&color=fff&bold=true", color: "F59E0B" }
    ];

    const logList = document.getElementById("log-list");
    let totalCount = 248;

    const renderLogs = (newLogAdded = false) => {
        logList.innerHTML = '';
        mockLogs.forEach((log, index) => {
            const li = document.createElement('li');
            li.className = `list-group-item p-3 d-flex align-items-center justify-content-between ${newLogAdded && index === 0 ? 'new-log-item' : 'log-item'}`;
            li.innerHTML = `
            <div class="d-flex align-items-center gap-3">
                    <img src="${log.img}" class="rounded-circle shadow-sm object-fit-cover" width="42" height="42" alt="${log.name}">
                    <div>
                        <h6 class="mb-0 text-white fw-medium">${log.name}</h6>
                        <small class="text-secondary">${log.role}</small>
                    </div>
                </div>
                <div class="text-end">
                    <span class="badge bg-success-subtle border border-success-subtle text-success mb-1">Present</span>
                    <br>
                    <small class="text-secondary"><i class="bi bi-clock me-1"></i>${log.time}</small>
                </div>
            `;
            logList.appendChild(li);
        });

        // Animate newly added log item
        if (newLogAdded) {
            const newLogEl = document.querySelector(".new-log-item");
            if (newLogEl) {
                newLogEl.animate([
                    { opacity: 0, transform: 'translateX(-30px)', backgroundColor: 'rgba(30, 41, 59, 1)' },
                    { opacity: 1, transform: 'translateX(0)', backgroundColor: 'transparent' }
                ], { duration: 600, easing: 'ease-out', fill: 'forwards' });
            }
        }
    };

    renderLogs();

    // 2. Fetch Logs Polling from SQLite instead of dummy data
    const fetchRealLogs = async () => {
        try {
            const res = await fetch("http://localhost:5000/api/logs");
            const data = await res.json();
            if(data && data.length > 0) {
                // If logs changed
                if(JSON.stringify(mockLogs) !== JSON.stringify(data)) {
                    mockLogs = data;
                    renderLogs(true);
                }
            }
        } catch(e) {
            console.log("Waiting for backend...");
        }
    };
    setInterval(fetchRealLogs, 2000);

    // 3. Profile Login Form Handling (Pass Details to Python, Python captures its own Video Feed)
    const loginForm = document.getElementById("profileLoginForm");
    const loginBtn = document.getElementById("loginBtn");
    const loginAlert = document.getElementById("loginAlert");

    if (loginForm) {
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            loginBtn.disabled = true;
            loginBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Python is physically grabbing 30 frames from scanner... hold still!';
            if(loginAlert) loginAlert.classList.add("d-none");
            
            const name = document.getElementById("name").value;
            const department = document.getElementById("department").value;
            const rollNo = document.getElementById("classRollNo").value;

            try {
                // We POST just details! Python grabs the frames from its active CV thread instantly!
                const response = await fetch("http://localhost:5000/api/profile/login", {
                    method: "POST",
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name,
                        department: department,
                        classRollNo: rollNo
                    }) // No images sent!
                });

                const data = await response.json();

                if (response.ok) {
                    loginBtn.innerHTML = '<i class="bi bi-check-circle-fill me-2"></i>Success!';
                    
                    setTimeout(() => {
                        const modalEl = document.getElementById("loginModal");
                        const modal = bootstrap.Modal.getInstance(modalEl);
                        if (modal) modal.hide();
                        
                        loginForm.reset();
                        loginBtn.disabled = false;
                        loginBtn.innerHTML = 'Authenticate & Login';
                    }, 1000);

                } else {
                    throw new Error(data.error || "Failed to save profile");
                }
            } catch (error) {
                console.error("Upload error:", error);
                if(loginAlert) {
                    loginAlert.textContent = "Error: " + error.message;
                    loginAlert.classList.remove("d-none");
                }
                loginBtn.disabled = false;
                loginBtn.innerHTML = 'Authenticate & Login';
            }
        });
    }
});
