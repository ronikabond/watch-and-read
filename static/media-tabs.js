(() => {
    const tabGroups = document.querySelectorAll(
        "[data-media-tabs]"
    );

    const controllers = [];


    tabGroups.forEach((tabsContainer) => {
        const tabList = tabsContainer.querySelector(
            ".media-tabs-list"
        );

        const tabs = Array.from(
            tabsContainer.querySelectorAll(
                ".media-tab"
            )
        );

        const grid = document.getElementById(
            tabsContainer.dataset.gridId
        );

        const emptyMessage = document.getElementById(
            tabsContainer.dataset.emptyId
        );

        const filterToolbar = tabsContainer.closest(
            ".media-filter-toolbar"
        );

        const genreSelect = filterToolbar
            ? filterToolbar.querySelector(
                "[data-genre-filter]"
            )
            : null;

        if (
            !tabList
            || !grid
            || tabs.length === 0
        ) {
            return;
        }


        let activeTab = null;

        let activeGenre = genreSelect
            ? genreSelect.value
            : "all";

        let switchTimer = null;


        function updateIndicator(tab) {
            tabList.style.setProperty(
                "--indicator-left",
                `${tab.offsetLeft}px`,
            );

            tabList.style.setProperty(
                "--indicator-width",
                `${tab.offsetWidth}px`,
            );
        }


        function filterCards() {
            const selectedType =
                activeTab.dataset.mediaFilter;

            const cards = Array.from(
                grid.querySelectorAll(
                    ".media-card[data-media-type]"
                )
            );

            let visibleCards = 0;


            cards.forEach((card) => {
                const matchesMediaType = (
                    selectedType === "all"
                    || card.dataset.mediaType
                        === selectedType
                );

                const matchesGenre = (
                    activeGenre === "all"
                    || card.dataset.mediaGenre
                        === activeGenre
                );

                const shouldShow = (
                    matchesMediaType
                    && matchesGenre
                );

                card.hidden = !shouldShow;

                card.classList.toggle(
                    "is-filtered-out",
                    !shouldShow,
                );

                card.setAttribute(
                    "aria-hidden",
                    String(!shouldShow),
                );

                if (shouldShow) {
                    visibleCards += 1;
                }
            });


            if (!emptyMessage) {
                return;
            }

            const filtersAreEmpty = (
                cards.length > 0
                && visibleCards === 0
            );

            emptyMessage.classList.toggle(
                "is-hidden",
                !filtersAreEmpty,
            );

            emptyMessage.textContent =
                filtersAreEmpty
                    ? (
                        "По выбранным виду медиа и жанру "
                        + "произведений пока нет."
                    )
                    : "";
        }


        function activateTab(
            tab,
            {
                animate = true,
                focus = false,
            } = {},
        ) {
            const wasActive = tab === activeTab;

            activeTab = tab;


            tabs.forEach((currentTab) => {
                const isActive =
                    currentTab === activeTab;

                currentTab.classList.toggle(
                    "is-active",
                    isActive,
                );

                currentTab.setAttribute(
                    "aria-selected",
                    String(isActive),
                );

                currentTab.tabIndex =
                    isActive ? 0 : -1;
            });


            grid.setAttribute(
                "aria-labelledby",
                activeTab.id,
            );

            updateIndicator(activeTab);


            if (focus) {
                activeTab.focus();

                activeTab.scrollIntoView({
                    behavior: "smooth",
                    block: "nearest",
                    inline: "center",
                });
            }


            if (wasActive && animate) {
                return;
            }

            window.clearTimeout(switchTimer);


            if (!animate) {
                grid.classList.remove(
                    "is-switching"
                );

                filterCards();

                return;
            }


            grid.classList.add(
                "is-switching"
            );

            switchTimer = window.setTimeout(
                () => {
                    filterCards();

                    window.requestAnimationFrame(
                        () => {
                            grid.classList.remove(
                                "is-switching"
                            );
                        },
                    );
                },
                160,
            );
        }


        tabs.forEach((tab) => {
            tab.addEventListener(
                "click",
                () => {
                    activateTab(tab);
                },
            );
        });

        if (genreSelect) {
            genreSelect.addEventListener(
                "change",
                () => {
                    activeGenre = genreSelect.value;

                    filterCards();
                },
            );
        }


        tabList.addEventListener(
            "keydown",
            (event) => {
                const currentTab =
                    event.target.closest(
                        ".media-tab"
                    );

                const currentIndex =
                    tabs.indexOf(currentTab);

                if (currentIndex === -1) {
                    return;
                }


                let nextIndex;

                if (event.key === "ArrowRight") {
                    nextIndex =
                        (currentIndex + 1)
                        % tabs.length;
                } else if (
                    event.key === "ArrowLeft"
                ) {
                    nextIndex =
                        (
                            currentIndex
                            - 1
                            + tabs.length
                        )
                        % tabs.length;
                } else if (event.key === "Home") {
                    nextIndex = 0;
                } else if (event.key === "End") {
                    nextIndex = tabs.length - 1;
                } else {
                    return;
                }


                event.preventDefault();

                activateTab(
                    tabs[nextIndex],
                    { focus: true },
                );
            },
        );


        const initiallySelectedTab = (
            tabs.find(
                (tab) => (
                    tab.getAttribute(
                        "aria-selected"
                    ) === "true"
                )
            )
            || tabs[0]
        );

        activateTab(
            initiallySelectedTab,
            { animate: false },
        );


        controllers.push({
            refresh() {
                window.clearTimeout(
                    switchTimer
                );

                grid.classList.remove(
                    "is-switching"
                );

                filterCards();
                updateIndicator(activeTab);
            },
        });
    });


    window.refreshMediaTabs = () => {
        controllers.forEach(
            (controller) => {
                controller.refresh();
            },
        );
    };


    window.addEventListener(
        "resize",
        window.refreshMediaTabs,
    );

    if (document.fonts) {
        document.fonts.ready.then(
            window.refreshMediaTabs
        );
    }
})();