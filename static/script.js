document.getElementById('gradingForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const mode = document.getElementById('mode').value;
    const submissionFile = document.getElementById('submissionFile').files[0];
    const rubricFile = document.getElementById('rubricFile').files[0];

    if (!submissionFile || !rubricFile) {
        alert("Please upload both files.");
        return;
    }

    // UI Loading State
    const btn = e.target.querySelector('button');
    const btnText = document.getElementById('btnText');
    const spinner = document.getElementById('loadingSpinner');
    const resultsArea = document.getElementById('resultsArea');

    btn.disabled = true;
    btnText.textContent = "Grading...";
    spinner.classList.remove('hidden');
    resultsArea.classList.add('hidden');

    // Prepare Data
    const formData = new FormData();
    formData.append('mode', mode);
    formData.append('submission_file', submissionFile);
    formData.append('rubric_file', rubricFile);

    try {
        const response = await fetch('/grade', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Grading failed");
        }

        const result = await response.json();
        renderResults(result);

    } catch (error) {
        alert("Error: " + error.message);
        console.error(error);
    } finally {
        btn.disabled = false;
        btnText.textContent = "Grade Assessment";
        spinner.classList.add('hidden');
    }
});

// --- PDF Logic ---
// renderPdf/renderPage moved to /viewer endpoint

function highlightCitations(citations) {
    const iframe = document.getElementById('pdf-frame');
    if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage({
            type: 'HIGHLIGHT',
            citations: citations
        }, '*'); // Use '*' for simplicity in this same-origin setup
    }

    // Ensure view is visible
    showSubmission();
    enterFocusMode();
}

function showSubmission() {
    const col = document.getElementById('colSubmission');
    col.classList.remove('hidden');
    col.classList.add('flex', 'flex-col');

    // Default to 3 cols (1-1-1)
    const grid = document.getElementById('resultsGrid');
    grid.classList.remove('md:grid-cols-2');
    grid.classList.add('md:grid-cols-3');
}

function hideSubmission() {
    const col = document.getElementById('colSubmission');
    col.classList.remove('flex', 'flex-col');
    col.classList.add('hidden');

    // Revert grid
    const grid = document.getElementById('resultsGrid');
    grid.classList.remove('md:grid-cols-3');
    grid.classList.add('md:grid-cols-2');

    exitFocusMode();
}

function enterFocusMode() {
    // 1. Hide Main Rubric Value
    document.getElementById('colRubric').classList.add('hidden');

    // 2. Show Pinned Rubric in Results column and sync content
    const rubricContent = document.getElementById('rubricView').textContent;
    document.getElementById('rubricPinnedContent').textContent = rubricContent;
    document.getElementById('rubricPinnedContainer').classList.remove('hidden');

    // 3. Expand Submission Column (Span 2 cols)
    document.getElementById('colSubmission').classList.add('md:col-span-2');

    // 4. Ensure Grid is correct (it should be allowed to reflow)
    // With 3 cols defined:
    // [Sub (span 2)] [Res (span 1)] = 3 units total. Perfect.
}

function exitFocusMode() {
    // 1. Show Main Rubric
    document.getElementById('colRubric').classList.remove('hidden');

    // 2. Hide Pinned Rubric
    document.getElementById('rubricPinnedContainer').classList.add('hidden');

    // 3. Contract Submission Column
    document.getElementById('colSubmission').classList.remove('md:col-span-2');
}

// --- Results Rendering Update ---
function renderResults(data) {
    document.getElementById('resultsArea').classList.remove('hidden');

    // Reset to 2-col view initially
    hideSubmission();

    // The backend now returns { result: {...}, submission_content: "...", rubric_content: "..." }
    const gradeResult = data.result || data;

    // View Toggle
    const subView = document.getElementById('submissionView');
    const pdfFrame = document.getElementById('pdf-frame');
    const rubView = document.getElementById('rubricView');

    if (rubView) rubView.textContent = data.rubric_content || "Rubric not available.";

    // Prepare the content but don't show the column yet
    if (data.file_type === 'pdf' && data.file_url) {
        subView.classList.add('hidden');
        pdfFrame.classList.remove('hidden');
        // Set Iframe Source
        pdfFrame.src = `/viewer?file=${encodeURIComponent(data.file_url)}`;
    } else {
        pdfFrame.classList.add('hidden');
        subView.classList.remove('hidden');
        subView.textContent = data.submission_content || "Content not available.";
    }

    document.getElementById('studentId').textContent = gradeResult.student_id;

    // Check for error state from backend
    if (gradeResult.submission_id === 'error' || (gradeResult.total_score === 0 && gradeResult.feedback.includes("Error"))) {
        document.getElementById('totalScore').textContent = "Error";
        document.getElementById('maxScore').textContent = "-";
        document.getElementById('overallFeedback').innerHTML = `<span class="text-red-600 font-bold">${gradeResult.feedback}</span>`;
    } else {
        document.getElementById('totalScore').textContent = gradeResult.total_score;
        document.getElementById('maxScore').textContent = gradeResult.max_score;
        document.getElementById('overallFeedback').textContent = gradeResult.feedback;
    }

    const container = document.getElementById('detailedResults');
    container.innerHTML = '';

    if (gradeResult.detailed_results) {
        gradeResult.detailed_results.forEach(item => {
            const criteriaName = Object.keys(item.criteria_scores)[0] || "Criteria";
            const score = item.score;

            // Interaction logic
            const hasCitations = item.citations && item.citations.length > 0;
            const cursorClass = hasCitations ? "cursor-pointer hover:bg-blue-50 hover:border-blue-300" : "";
            const citationBadge = hasCitations ? `<span class="text-xs bg-blue-100 text-blue-800 px-1 rounded ml-2">Show Ref</span>` : "";

            const div = document.createElement('div');
            div.className = `p-3 border rounded bg-white transition text-sm ${cursorClass}`;
            div.innerHTML = `
                <div class="flex justify-between font-semibold text-gray-800">
                    <div>${criteriaName} ${citationBadge}</div>
                    <span>${score} pts</span>
                </div>
                <p class="text-xs text-gray-600 mt-1">${item.feedback}</p>
            `;

            if (hasCitations) {
                div.onclick = () => highlightCitations(item.citations);
            }

            container.appendChild(div);
        });
    }
}

// --- Canvas Integration ---

function switchTab(tab) {
    if (tab === 'manual') {
        document.getElementById('manualSection').classList.remove('hidden');
        document.getElementById('canvasSection').classList.add('hidden');
        document.getElementById('tabManual').className = "mr-4 pb-2 border-b-2 border-blue-600 font-bold";
        document.getElementById('tabCanvas').className = "pb-2 border-b-2 border-transparent text-gray-500";
    } else {
        document.getElementById('manualSection').classList.add('hidden');
        document.getElementById('canvasSection').classList.remove('hidden');
        document.getElementById('tabManual').className = "mr-4 pb-2 border-b-2 border-transparent text-gray-500";
        document.getElementById('tabCanvas').className = "pb-2 border-b-2 border-blue-600 font-bold";
    }
}

async function connectCanvas() {
    const url = document.getElementById('canvasUrl').value;
    const key = document.getElementById('canvasKey').value;

    try {
        const res = await fetch('/canvas/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_url: url, api_key: key })
        });
        const data = await res.json();

        if (data.status === 'success') {
            const select = document.getElementById('courseSelect');
            select.innerHTML = '<option value="">Select a Course...</option>';
            data.courses.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.textContent = c.name;
                select.appendChild(opt);
            });
            document.getElementById('canvasSelect').classList.remove('hidden');
        } else {
            alert("Connection error");
        }
    } catch (e) {
        alert("Failed to connect: " + e);
    }
}

async function loadAssignments() {
    const courseId = document.getElementById('courseSelect').value;
    const url = document.getElementById('canvasUrl').value;
    const key = document.getElementById('canvasKey').value;

    if (!courseId) return;

    // Using GET params for simplicity in proto
    const res = await fetch(`/canvas/assignments/${courseId}?api_url=${encodeURIComponent(url)}&api_key=${encodeURIComponent(key)}`);
    const assignments = await res.json();

    const select = document.getElementById('assignmentSelect');
    select.innerHTML = '<option value="">Select Assignment...</option>';
    assignments.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.name;
        select.appendChild(opt);
    });
}

async function importSubmissions() {
    const courseId = document.getElementById('courseSelect').value;
    const assignmentId = document.getElementById('assignmentSelect').value;
    const url = document.getElementById('canvasUrl').value;
    const key = document.getElementById('canvasKey').value;

    const res = await fetch('/canvas/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            course_id: courseId, assignment_id: assignmentId,
            api_url: url, api_key: key
        })
    });

    const data = await res.json();
    if (data.status === 'success') {
        const list = document.getElementById('submissionList');
        list.innerHTML = '';
        data.submissions.forEach(s => {
            const li = document.createElement('li');
            li.className = "flex justify-between items-center p-2 border-b";
            li.innerHTML = `
                <span>${s.student_name} (${s.content_type}) - ${s.workflow_state}</span>
                <button class="bg-blue-500 text-white px-2 py-1 text-sm rounded" onclick="gradeCanvasItem(${s.id})">Grade</button>
            `;
            list.appendChild(li);
        });
        document.getElementById('importResults').classList.remove('hidden');
    }
}

async function gradeCanvasItem(studentId) {
    const resultsArea = document.getElementById('resultsArea');
    let postBtn = document.getElementById('postToCanvasBtn');

    if (!postBtn) {
        postBtn = document.createElement('button');
        postBtn.id = 'postToCanvasBtn';
        postBtn.textContent = "Post Grade to Canvas";
        postBtn.className = "mt-4 bg-green-600 text-white p-3 rounded w-full hover:bg-green-700 font-bold";
        postBtn.onclick = () => postGradeToCanvas(studentId);
        resultsArea.appendChild(postBtn);
    } else {
        postBtn.onclick = () => postGradeToCanvas(studentId);
    }

    // Switch to results view as if logic ran
    document.getElementById('resultsArea').classList.remove('hidden');
    // For proto: clear old feedback
    document.getElementById('overallFeedback').textContent = "Draft Grade for Canvas Submission (Mocked Content)";
    document.getElementById('totalScore').textContent = "0";
    document.getElementById('maxScore').textContent = "10";

    alert("In this prototype, we mock the grading step for imported items because file download logic is pending. \n\nYou can input a simulated score below and click 'Post to Canvas' to verify the API write-back.");
}

async function postGradeToCanvas(studentId) {
    // In a real app, these values come from the DOM after grading
    // For proto verification, we let the user know, or just simulate a score if empty
    let score = document.getElementById('totalScore').textContent;
    const feedback = document.getElementById('overallFeedback').textContent;

    // Allow user to prompt for score if it's 0/mock
    if (score === "0") {
        score = prompt("Enter a score to post (0-10):", "10");
        document.getElementById('totalScore').textContent = score;
    }

    const courseId = document.getElementById('courseSelect').value;
    const assignmentId = document.getElementById('assignmentSelect').value;
    const url = document.getElementById('canvasUrl').value;
    const key = document.getElementById('canvasKey').value;

    if (!score || !courseId) return;

    try {
        const res = await fetch('/canvas/post_grade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: courseId, assignment_id: assignmentId, student_id: studentId,
                grade: parseFloat(score), comment: feedback,
                api_url: url, api_key: key
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            alert("Grade posted successfully!");
        } else {
            alert("Failed to post grade.");
        }
    } catch (e) {
        alert("Error posting grade: " + e);
    }
}
