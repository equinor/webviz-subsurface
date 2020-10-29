window.$docsify = {
    logo: "./webviz-logo.svg",
    homepage: "INTRODUCTION.md",    
    name: "Webviz",
    loadSidebar: "sidebar.md",
    subMaxLevel: 4,
    copyCode: {
        buttonText : "Copy",
    },
    tabs: {
        sync: false,
        theme: "material",
        tabHeadings: false
    },
    search: {
        paths: ["/", "/webviz-config", "/webviz-subsurface"],
        depth: 6,
        hideOtherSidebarContent: true,
        maxAge: 30e3 // default cache maxage one day (8.64e7 ms) - old cached content can be confusing if user changes installed webviz plugins
    }
}