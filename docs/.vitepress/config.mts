import { defineConfig } from "vitepress";
import { withMermaid } from "vitepress-plugin-mermaid";

export default withMermaid(
  defineConfig({
    title: "WorldGuessr Interview Handbook",
    description: "An interview-focused FastAPI, React, system-design, and AWS handbook grounded in the WorldGuessr codebase.",
    cleanUrls: true,
    lastUpdated: true,
    themeConfig: {
      nav: [
        { text: "Handbook", link: "/README" },
        { text: "Backend", link: "/01-backend/README" },
        { text: "Frontend", link: "/02-frontend/README" },
        { text: "Architecture", link: "/03-system-design/README" },
        { text: "AWS", link: "/04-cloud-deploy/README" },
      ],
      sidebar: [
        {
          text: "WorldGuessr handbook",
          items: [
            { text: "Overview", link: "/README" },
            { text: "01 · Backend with FastAPI", link: "/01-backend/README" },
            { text: "02 · Frontend with React", link: "/02-frontend/README" },
            { text: "03 · Architecture", link: "/03-system-design/README" },
            { text: "04 · AWS deployment", link: "/04-cloud-deploy/README" },
          ],
        },
      ],
      outline: { level: [2, 3], label: "On this page" },
      search: { provider: "local" },
      footer: {
        message: "WorldGuessr full-stack and cloud handbook",
        copyright: "Repository documentation",
      },
    },
    mermaid: {
      theme: "default",
    },
  }),
);
