document.addEventListener("DOMContentLoaded", () => {
    const title = document.querySelector("h1");
    if (!title) {
        return;
    }

    title.animate(
        [
            { opacity: 0, transform: "translateY(8px)" },
            { opacity: 1, transform: "translateY(0)" },
        ],
        {
            duration: 450,
            easing: "ease-out",
            fill: "forwards",
        }
    );
});