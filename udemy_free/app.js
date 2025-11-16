(() => {
  const API_URL = "api/courses.json";
  const PAGE_SIZE = 50;

  const elements = {
    meta: document.getElementById("meta"),
    status: document.getElementById("status"),
    courses: document.getElementById("courses"),
    search: document.getElementById("search"),
    count: document.getElementById("count"),
    refresh: document.getElementById("refresh"),
    pagination: document.getElementById("pagination"),
    donateFab: document.getElementById("donateFab"),
    donateModal: document.getElementById("donateModal"),
    donateClose: document.getElementById("donateClose"),
    donateBackdrop: document.getElementById("donateBackdrop"),
  };

  let allCourses = [];
  let currentCourses = [];
  let currentPage = 1;

  function formatUpdatedAt(updatedAt) {
    if (!updatedAt) return "Chưa có dữ liệu.";
    try {
      const d = new Date(updatedAt);
      if (Number.isNaN(d.getTime())) return updatedAt;
      return d.toLocaleString();
    } catch (e) {
      return updatedAt;
    }
  }

  function deriveTitleFromUrl(url) {
    try {
      const u = new URL(url);
      const parts = u.pathname.split("/").filter(Boolean);
      let slug = parts[parts.length - 1] || "";
      // Typical Udemy path: /course/<slug>/
      if (parts.length >= 2 && parts[0] === "course") {
        slug = parts[1];
      }
      if (!slug) return url;
      return decodeURIComponent(slug.replace(/-/g, " "));
    } catch (e) {
      return url;
    }
  }

  function renderCoursesPage() {
    elements.courses.innerHTML = "";

    if (!currentCourses.length) {
      elements.status.textContent =
        "Không có khóa học nào trong lần build hiện tại.";
      elements.count.textContent = "";
      return;
    }

    const total = currentCourses.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    const start = (currentPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    const pageItems = currentCourses.slice(start, end);

    elements.status.textContent = "";
    elements.count.textContent = `${total} khóa học (trang ${currentPage}/${totalPages})`;

    const fragment = document.createDocumentFragment();
    pageItems.forEach((course) => {
      const card = document.createElement("article");
      card.className = "course";

      const titleText = course.title || deriveTitleFromUrl(course.url);

      if (course.image_url) {
        const img = document.createElement("img");
        img.className = "course-image";
        img.src = course.image_url;
        img.alt = titleText;
        img.loading = "lazy";
        card.appendChild(img);
      }

      const title = document.createElement("h2");
      title.textContent = titleText;
      card.appendChild(title);

      const urlLink = document.createElement("a");
      urlLink.href = course.url;
      urlLink.target = "_blank";
      urlLink.rel = "noopener noreferrer";
      urlLink.textContent = "Mở khóa học (Udemy)";
      card.appendChild(urlLink);

      const meta = document.createElement("p");
      meta.className = "course-meta";
      const coupon = course.coupon_code ? course.coupon_code : "N/A";
      meta.textContent = `Coupon: ${coupon}`;
      card.appendChild(meta);

      fragment.appendChild(card);
    });

    elements.courses.appendChild(fragment);
    renderPagination(totalPages);
  }

  function renderPagination(totalPages) {
    if (!elements.pagination) return;
    elements.pagination.innerHTML = "";

    if (totalPages <= 1) {
      return;
    }

    const prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.textContent = "Trang trước";
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage -= 1;
        renderCoursesPage();
      }
    });

    const nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.textContent = "Trang sau";
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener("click", () => {
      if (currentPage < totalPages) {
        currentPage += 1;
        renderCoursesPage();
      }
    });

    const info = document.createElement("span");
    info.className = "pagination-info";
    info.textContent = `Trang ${currentPage} / ${totalPages}`;

    elements.pagination.appendChild(prevBtn);
    elements.pagination.appendChild(info);
    elements.pagination.appendChild(nextBtn);
  }

  function applyFilter() {
    const term = elements.search.value.trim().toLowerCase();
    if (!term) {
      currentCourses = allCourses.slice();
    } else {
      currentCourses = allCourses.filter((course) => {
        const text = `${course.url} ${course.coupon_code || ""} ${
          course.title || ""
        }`.toLowerCase();
        return text.includes(term);
      });
    }
    currentPage = 1;
    renderCoursesPage();
  }

  async function loadCourses() {
    elements.status.textContent = "Đang tải dữ liệu...";
    try {
      const res = await fetch(`${API_URL}?_=${Date.now()}`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      allCourses = Array.isArray(data.courses) ? data.courses : [];
      currentCourses = allCourses.slice();
      elements.meta.textContent = `Lần build gần nhất: ${formatUpdatedAt(
        data.updated_at
      )}`;
      currentPage = 1;
      renderCoursesPage();
    } catch (err) {
      console.error(err);
      elements.status.textContent =
        "Không tải được dữ liệu. Hãy kiểm tra lại file api/courses.json hoặc đợi workflow cập nhật.";
      elements.count.textContent = "";
    }
  }

  elements.search.addEventListener("input", () => {
    applyFilter();
  });

  if (elements.refresh) {
    elements.refresh.addEventListener("click", () => {
      loadCourses();
    });
  }

  function openDonateModal() {
    if (!elements.donateModal) return;
    elements.donateModal.hidden = false;
  }

  function closeDonateModal() {
    if (!elements.donateModal) return;
    elements.donateModal.hidden = true;
  }

  if (elements.donateFab) {
    elements.donateFab.addEventListener("click", openDonateModal);
  }

  if (elements.donateClose) {
    elements.donateClose.addEventListener("click", closeDonateModal);
  }

  if (elements.donateBackdrop) {
    elements.donateBackdrop.addEventListener("click", closeDonateModal);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeDonateModal();
    }
  });

  document.addEventListener("DOMContentLoaded", loadCourses);
})();
