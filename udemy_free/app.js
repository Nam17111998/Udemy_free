(() => {
  const API_URL = "api/courses.json";

  const elements = {
    meta: document.getElementById("meta"),
    status: document.getElementById("status"),
    courses: document.getElementById("courses"),
    search: document.getElementById("search"),
    count: document.getElementById("count"),
    refresh: document.getElementById("refresh"),
  };

  let allCourses = [];

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

  function renderCourses(courses) {
    elements.courses.innerHTML = "";
    if (!courses.length) {
      elements.status.textContent =
        "Không có khóa học nào trong lần build hiện tại.";
      elements.count.textContent = "";
      return;
    }

    elements.status.textContent = "";
    elements.count.textContent = `${courses.length} khóa học`;

    const fragment = document.createDocumentFragment();
    courses.forEach((course) => {
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
  }

  function applyFilter() {
    const term = elements.search.value.trim().toLowerCase();
    if (!term) {
      renderCourses(allCourses);
      return;
    }
    const filtered = allCourses.filter((course) => {
      const text = `${course.url} ${course.coupon_code || ""} ${
        course.title || ""
      }`.toLowerCase();
      return text.includes(term);
    });
    renderCourses(filtered);
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
      elements.meta.textContent = `Lần build gần nhất: ${formatUpdatedAt(
        data.updated_at
      )}`;
      renderCourses(allCourses);
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

  document.addEventListener("DOMContentLoaded", loadCourses);
})();

