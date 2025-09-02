# KireMisu – Product Requirements Document (PRD)

Creator/Owner: KarmicJuju (GitHub username)

## 1. Vision

KireMisu is a self-hosted, cloud-first manga reader and library management system (rebranded from the previous project) aimed at bringing together the best aspects of existing solutions like Readarr, Houdoku, Kindle, and MangaDex into one unified platform. The vision is to create a personal manga management hub – similar in spirit to Kavita – that offers rich metadata, offline access, and highly customizable organization, all within a modern web-based interface. This product is being built primarily for the creator's own use (as an avid manga reader and self-hoster), but it will also cater to a broader community of manga enthusiasts who prefer running their own servers.

### Key high-level goals include:

**Unified Library**: Allow users to collect, organize, and read all their manga in one place, whether acquired from personal files or fetched via MangaDex integration.

**Cloud-First & Self-Hosted**: Emphasize a self-hostable web application that can run in a Docker container or on a personal server/VPS (accessible via browser). This avoids the bloat of heavy desktop apps (no Electron) in favor of better performance and deployability on one's own infrastructure.

**Metadata-Rich Experience**: Leverage metadata extensively – automatic enrichment from external sources (e.g. MangaDex) combined with user curation – to provide rich information (genres, authors, tags, covers, etc.) and powerful filtering for the collection. Metadata will drive organization and personalization of the reading experience.

**Personalization & Advanced Features**: Offer features for power users such as custom tagging, file renaming schemes, annotation of chapters, and an extensible API for integrations. These advanced capabilities should enhance how users curate and interact with their collection beyond basic reading.

**Offline Capability**: Ensure users can enjoy their manga offline by providing options to download or export content for reading on the go. Even in a self-hosted context, KireMisu will support offline use-cases (e.g. exporting a series to a device) so that lack of internet connectivity doesn't hinder the reading experience.

In summary, the vision for KireMisu is a flexible, user-centric manga library system that balances ease-of-use for casual readers with powerful tools for collectors and self-hosting enthusiasts. It is a fresh start building on lessons learned from the earlier project – focusing more on practical user experience and robust design rather than premature technical choices.

## 2. Target Audience & Use Cases

Because KireMisu is being created by an enthusiast for personal use, it naturally targets users similar to the creator. However, it's designed to serve a spectrum of manga readers who are comfortable self-hosting or want greater control over their library. The primary user personas include:

**Self-Hosting Enthusiasts / Server Admins**: Users who love running their own services (e.g. in Docker or Kubernetes) and want a manga server they control. They will appreciate easy deployment and the ability to host KireMisu on their own hardware or cloud instances.

**Casual Readers**: Users who primarily want to read manga in one convenient place. For them, the system should be simple to navigate, with an intuitive UI to browse their collection or read new chapters without fuss. They benefit from the unified library and easy search/download from MangaDex, but may not use advanced features immediately.

**Collectors & Curators**: Users with large personal manga collections who care about rich metadata and organization. They will use features like metadata editing, custom tags, curated reading lists, and cover management to organize their library in detail. This group values the ability to fine-tune how their collection is presented and categorized.

**Power Users / Tinkerers**: Tech-savvy users who enjoy customizing workflows. They will take advantage of advanced capabilities such as defining file naming conventions, bulk-renaming files according to metadata, organizing the file structure, and using the exposed API to create scripts or automation (for example, to automatically fetch new releases, or integrate with other tools). This persona will stress-test the flexibility of KireMisu's design.

**Offline Readers**: Users who often need to read without internet access (for instance, on commutes or travel). They value being able to download manga for offline reading onto their devices or external storage. KireMisu should make it easy to export or sync content for offline use so that these users can take their library with them.

By catering to these audiences, KireMisu aims to cover a range of use cases – from someone setting up a small private manga server for casual reading, to a manga archivist maintaining a detailed library with custom metadata, to a developer integrating the app into a larger automation workflow. The product should remain user-friendly for the casual user, yet powerful and extensible for the advanced user.

*(Note: Multi-user support (e.g. families or friend groups sharing a server) is recognized as a potential future audience, but in the initial release KireMisu will primarily target a single-user or single-admin scenario. Multi-user functionality is a "nice-to-have" that may be added later, see Future Expansion.)*

## 3. Core Functional Requirements

This section outlines the key features and workflows KireMisu will support at launch. Each subsection describes a functional area, the requirements for that area, and any relevant decisions or trade-offs based on the project's vision. The focus is on features that provide immediate user value and lessons learned from the previous iteration, ensuring a practical and robust initial release.

### 3.1 Media Management (Storage & Import)

KireMisu will manage manga files provided by the user in a robust, self-hosted storage environment. This includes handling how content is imported, stored, and kept in sync with the file system:

**Local/Network Storage Integration**: The application will use user-designated storage locations (such as a directory on the host system or a mounted network drive/NAS) as the source of truth for manga files. Users (or admins) can add library paths in the app, which the system will then scan and index. (In a container/Kubernetes deployment, this corresponds to mounting volumes or using Persistent Volume Claims to point the app to the manga files.)

**Manual Import**: Users can manually trigger the app to import or re-scan a specified folder path for new manga content. This allows users to add new files to their collection by placing them in the storage location and instructing KireMisu to index them. The app should allow configuration of multiple library paths if needed (e.g., one for manga, one for light novels, etc., as future flexibility).

**Scheduled Library Sync**: Users can configure periodic synchronization jobs for each storage location. For example, a user could set the library to sync every night or at a regular interval, ensuring the app's database stays up-to-date with the file system. This is useful for large libraries or network-mounted storage. The default sync frequency will be configurable (daily, weekly, or manual-only) to balance freshness with system resources.

**Storage Management**: The app does not physically move or alter the original files on disk unless explicitly directed (e.g., by a rename operation – see Renaming section). KireMisu acts as an index and viewer. Removing a series from the app will not delete the files from disk by default, to prevent accidental data loss. (Users might get an option to "remove from library" vs "delete from disk" with appropriate warnings.)

**Decisions & Trade-offs**: These choices favor reliability, predictable resource usage, and user control. Relying on explicit storage paths and external volumes aligns with the self-hosted nature and cloud-native deployment, where volumes are mounted into containers. This ensures that the manga collection is centralized and backup-friendly (the user can back up the NAS or volume itself). The trade-off is that initial configuration requires a technical user to set up the volume or path, but this is acceptable given our target audience (self-hosters). The scheduled sync approach is more predictable and allows users to control when system resources are used for library maintenance, avoiding performance overhead from continuous monitoring. Overall, treating the file system as the source of truth provides transparency – users can always access their files directly – and reduces risk of vendor lock-in or data loss.

### 3.2 Metadata Management & Tagging

Rich metadata is a core value of KireMisu. The system will automatically fetch information for each manga and allow extensive user curation of metadata:

**Automated Metadata Enrichment**: Upon adding a new series, KireMisu will fetch metadata from an external source (starting with the MangaDex API) to populate details like title, author/artist, genres, synopsis, cover image, release status, etc. This gives users a good default metadata set without manual effort. The system should handle API rate limits gracefully (caching results or spreading out requests) and fall back to basic info if the external API is unavailable.

**Editable Metadata Fields**: Users can manually edit and override metadata on a per-series (or even per-chapter) basis. Every field fetched (such as title, summary, author, genre tags, etc.) should be editable through the UI in case the user wants to correct information or prefer a different naming. User edits are saved in the app's database and won't be overwritten by future auto-updates unless the user chooses to refresh metadata.

**Custom Tags & Annotations**: Beyond standard metadata, the user can add custom tags or notes to a series or chapter. For example, a user might tag a series as "Summer 2025" or "Wishlist" or mark a chapter with "favorite" or add a personal note about it. These tags/annotations become part of the metadata and can be used in filtering and search. This feature recognizes that "metadata is king," and giving users flexibility to tag and annotate will help them organize content in whatever way they find meaningful.

**Cover Art Management**: Users can manage cover images for each series – either using the default from MangaDex (or other source) or uploading a custom cover. The app will cache thumbnails of covers for performance, and possibly generate thumbnails for chapters if needed. If a user is unhappy with an automatically fetched cover or if none is available (for personal content), they can upload their own image.

**Bulk Metadata Operations**: Provide utilities for bulk actions, such as selecting multiple series and refreshing their metadata from source, or editing a field (like tag or category) across many items at once. This helps in initial library setup where a user might want to tag dozens of series quickly or standardize some field.

**Decisions & Trade-offs**: Automating metadata fetch from MangaDex greatly enhances user experience by populating details without effort, but it introduces an external dependency – if MangaDex is down or changes API, the feature could be impacted. Mitigation will include caching and allowing manual edits as a fallback. Empowering users to edit and tag freely means the data model must be flexible; a document-oriented database (NoSQL) is preferred to accommodate varying fields and new tags without complex migrations. This aligns with the "flexible schema" approach. The trade-off is that we assume users interested in these features are willing to spend time curating metadata; casual readers may ignore these capabilities, which is fine – the UI will make them available but not intrusive. The system should also index relevant metadata fields to keep searches and filtering snappy despite the richness of data.

### 3.3 Bulk Renaming & File Organization

To satisfy power users and collectors, KireMisu will include features to reorganize and rename the actual files on disk according to user-defined conventions, all optionally and under user control:

**Custom Naming Schemes**: Users can define how they want their manga files and folders named, using metadata variables. For example, a user might specify a template like: `SeriesTitle/Volume 01/SeriesTitle - c001.cbz` or any pattern that includes metadata (series title, volume number, chapter number, chapter title, etc.). The app will provide a UI to configure these naming templates (possibly with presets or a small scripting syntax).

**Bulk Renaming Tool**: Once a naming scheme is set, the user can trigger a bulk rename for a given series (or the entire library). KireMisu will then rename the files and folders on the filesystem to match the chosen convention (e.g., rename all chapters of Naruto to "Naruto - Ch.001 – Title.cbz", etc.). This feature helps in keeping the underlying file structure neat, especially if the user intends to manage or use the files outside the app as well.

**Organization (Move Files)**: In addition to renaming, users may choose to have KireMisu reorganize files into a directory structure. For instance, ensure each series has its own folder, optionally group by first letter or some category if desired. This would involve moving files/folders as needed. Because this can be a heavy operation, it will likely be a manual on-demand action (not automatic on every metadata change).

**Simulation & Safety Checks**: Renaming/organizing will include a "dry-run" preview showing what changes will be made, so the user can review and confirm. The system should also handle conflicts or duplicates gracefully (e.g., if two chapters would end up with the same name, the app should warn or adjust). These safeguards prevent accidental file mix-ups or data loss.

**Integration with Metadata**: The renaming tool is tightly linked with metadata management – it uses the metadata to generate names. Thus, any changes in metadata (like editing a title or numbering) can prompt the user to re-run the renaming if they want the files to reflect those updates.

**Decisions & Trade-offs**: Providing a renaming and reorganization feature caters to power users who want a polished collection, and it leverages the rich metadata the system maintains. The main trade-off is complexity and risk: moving files around can potentially break things. To mitigate this, KireMisu treats these operations as advanced features – the default usage doesn't force anyone to rename files, it's opt-in. Also, heavy file operations might be slow for large libraries, so the feature will be implemented carefully, possibly with background processing or one-series-at-a-time limits to avoid locking up the app. This feature significantly differentiates KireMisu for collectors, as not all manga management apps allow direct filesystem reorganization easily. It turns the app into a powerful library maintenance tool in addition to a reader.

### 3.4 Custom Lists & Advanced Filtering

KireMisu will allow users to create custom groupings of manga (beyond the standard metadata categories) and to filter/browse their collection in flexible ways:

**User-Created Reading Lists**: Users can create their own lists/collections and add series to them manually. For example, a user might have a list called "Currently Reading", "Favorites", "To Read Next", or thematic lists like "Best Cyberpunk Manga". A series can belong to multiple user-defined lists simultaneously. These lists help users curate subsets of their library for easy access or sharing (if multi-user sharing comes in future).

**Smart Lists (Future)**: (This may be a future enhancement, but worth noting) The system could support automatically populated lists based on criteria (e.g., "Unfinished Series" or "Newly Added")—initial version may include a couple of these as default filters rather than fully user-programmable smart lists.

**Advanced Filtering**: Users can filter the library by various metadata attributes: by tags, genres, author/artist, publication status (ongoing/completed), maturity rating, language, etc. The UI will provide filter controls so users can, for example, narrow down to all "Fantasy" genre manga that are completed series with a "Must Read" tag. Filters can be combined (AND logic) for powerful search within the library.

**Search**: A search function will allow quick keyword searches across titles, authors, and possibly tags. This search should be instant and cover both the user's library and optionally extend to MangaDex (see Integration below) if nothing is found locally. For local search, an indexed database ensures quick results even for large libraries.

**Sort & View Options**: In addition to filtering, users can sort the library (by title, date added, release year, etc.) and choose different view modes (grid of cover thumbnails vs. list view with details). These are standard UI capabilities to improve browsing comfort.

**Decisions & Trade-offs**: High customizability in filtering and lists adds complexity to the UI and requires efficient querying of the data. Using a document-oriented or well-indexed database is crucial for performance here. The benefit is a highly personalized experience for the user – they can essentially use KireMisu as a tool to curate their collection in arbitrary ways, not just the one-size-fits-all categorization. A potential trade-off is the need to educate the user (especially casual ones) about these features; the design should keep the basics (like a simple search or a default "All manga" view) very straightforward, with advanced filtering options tucked in an expandable panel or an "Advanced Search" dialog to not overwhelm newcomers. By launching with robust filtering and list features, we ensure that as the user's collection grows, the app remains navigable and useful, avoiding the common problem of a large library becoming unwieldy.

### 3.5 MangaDex Integration & Watching System

KireMisu will integrate with MangaDex (a popular online manga catalog and source) to enhance content acquisition and provide a "Watching" system for tracking new releases:

**Search & Add from MangaDex**: Users can search the MangaDex database from within KireMisu's interface. For example, if a user wants to add a new series they don't have files for, they can type the title in a search bar. The app will use the MangaDex API to search for the title and display results (title, cover, description). The user can then select a series and either import its metadata (to create a placeholder entry in their library) or directly download chapters into their library.

**Watching System for New Releases**: Users can mark series as "Watching" to track new chapter releases from MangaDex. This creates a polling-based notification system that:
- Allows users to follow ongoing series without manually checking for updates
- Polls MangaDex API on a configurable schedule (default: daily, configurable from hourly to weekly)
- Maintains a "Watched Series" list in the UI showing series status and available new chapters
- Provides notifications/badges when new chapters are detected
- Offers one-click download options for newly available chapters
- Respects MangaDex API rate limits through intelligent scheduling and caching

**Watching List Management**: The watching functionality includes:
- **Add to Watch List**: Users can add series to their watching list from search results or existing library items
- **Watch Status Indicators**: Clear UI indicators showing which series are being watched and their update status
- **New Chapter Notifications**: Visual indicators (badges, highlights) when new chapters are detected
- **Batch Actions**: Options to download multiple new chapters or mark notifications as seen
- **Watch Settings**: Per-series settings for notification preferences and auto-download options

**Reading Progress Sync**: If the user also reads on MangaDex (e.g., via their account on other devices), KireMisu will support bi-directional progress sync. This means if you've read up to chapter X on MangaDex, the app can reflect that and mark those chapters as read in your library, and conversely, if you read a chapter in KireMisu, it can update your MangaDex account's progress.

**Polling & Performance Optimization**: The watching system is designed for efficiency:
- **Intelligent Scheduling**: Staggers API calls across watched series to avoid rate limiting
- **Differential Updates**: Only checks for changes since last poll, reducing API calls
- **Configurable Intervals**: Users can set polling frequency per series or globally (hourly, daily, weekly)
- **Batch Processing**: Groups multiple series checks into efficient API batches where possible
- **Error Handling**: Graceful handling of API failures with automatic retry logic and user notifications

**Respecting Limits & Caching**: Because we rely on an external service, the integration will be built with respect to MangaDex's API limits. The app should cache results (for example, store search results or metadata so it doesn't fetch repeatedly) and stagger polling requests to avoid overloading or getting blocked. The watching system will include exponential backoff for failed requests and intelligent rate limiting.

**Future Source Integrations**: (While MangaDex is the primary source for launch, the system architecture will keep in mind the possibility of integrating other manga sources or content providers in the future, via a plugin system or additional APIs. However, initial focus is MangaDex.)

**Decisions & Trade-offs**: The watching system provides a superior user experience by focusing on the actual user need: knowing when new content is available. This approach eliminates filesystem complexity, improves performance predictability through scheduled polling, enhances user experience with proactive notifications about content they care about, reduces system overhead compared to continuous monitoring, and provides better user control over what's watched and notification frequency. The trade-off is dependence on external APIs for the watching functionality, but this is mitigated by graceful degradation (the core library features work independently) and the fact that this directly serves user needs better than filesystem monitoring. Integrating MangaDex greatly increases the value of KireMisu by combining the breadth of an online catalog with the control of a personal library.

### 3.6 Chapter Annotation & Notes

A standout feature for KireMisu is the ability for readers to annotate chapters, bringing an interactive note-taking capability to manga reading:

**Per-Chapter Annotations**: Users can add personal notes or annotations to a chapter they are reading. This could be implemented as a text note associated with the chapter (for example, "Chapter 5: This is where character X first appears," or "Amazing fight scene on page 10!"). The UI for this might be a simple sidebar or overlay in the reader where the user can type and save notes.

**Highlight or Bookmark Pages (Stretch Goal)**: If technically feasible, allow users to mark specific pages or panels. For instance, a user might want to bookmark a favorite page. Full highlighting on image-based content is complex (since we can't highlight text as in an e-book), so initially, annotation will likely be at chapter-level or page-level bookmarks rather than freeform highlights on the images.

**Viewing and Managing Notes**: The app will provide a way to view all annotations a user has made. This could be through an "Annotations" section in the UI or via each chapter's info. For example, a chapter that has a note could show an icon in the chapter list. Users can click to view or edit their note. There should also be a way to export or at least back up these notes (since they might be valuable user data).

**Context in Reading Experience**: When a user re-reads a chapter or comes back to it, their notes should be easily accessible – potentially popping up or indicated in the reader. The goal is to enrich the reading experience, almost like how Kindle allows notes and highlights on books. This is particularly useful for users who study artwork, translate manga, or just want to record thoughts as they read.

**Decisions & Trade-offs**: Annotation is a niche but powerful feature for a subset of users who engage deeply with content. Including it at launch differentiates KireMisu (few manga servers have this built-in). The trade-off is the added complexity in the reading interface and the need to store these notes reliably. Notes will be stored in the app database (likely associated with user and chapter IDs). Since we are currently single-user focused, the notes are just the one user's, simplifying things (no need for multi-user note-sharing yet). We must ensure the UI doesn't get cluttered for those who don't use annotations – the feature should be present but unobtrusive (perhaps a small "Add Note" button in the reader view). Overall, this caters to power users/collectors who treat their library as a research or review archive, and it aligns with the emphasis on metadata and user-generated data (notes being a form of metadata the user adds).

### 3.7 Public API & Automation

To empower power users and support integration with other tools, KireMisu will expose a secure Application Programming Interface (API) covering key functionalities:

**RESTful API Endpoints**: Most core actions in the app will have corresponding API endpoints. Examples: retrieving the list of series (and their metadata), searching the library, adding a new series (or triggering a library scan), marking a chapter as read, downloading a chapter file, and so on. This essentially allows any external script or application to do what a user could do through the UI.

**API Use Cases**: With a public API, users could write small programs or use automation platforms to extend KireMisu. For instance, a user could schedule a script (via Cron) that hits an endpoint to auto-download new chapters for followed series every day. Or integrate with a Discord bot to display what they're reading. Or build a mobile companion app that talks to their KireMisu server. By providing the API, we don't have to build all these things ourselves – we enable the community or the user to build what they need on top of the platform.

**Security & Authentication**: The API will be secured. Likely, KireMisu will require an API key or token (issued to the user) that must be included in API requests. Since initially it's single-user, we can have a single global API token or a simple token-based auth. In the future, if multi-user is introduced, the API would need user-specific tokens with permissions. All API access should be over HTTPS (when deployed properly) to protect credentials and data. The user will manage their API key in the settings and can regenerate or revoke it if needed.

**Documentation**: There will be documentation (or an interactive API docs page) describing how to use the API. This is important so that power users know what is available and how to format requests. We might use an OpenAPI (Swagger) specification or simply a written doc in the project README/wiki.

**Rate limiting & Performance**: To prevent abuse or accidental overload, the API may implement basic rate limiting (particularly for expensive operations like re-scanning library). But since this is self-hosted and single-user, we expect well-behaved use; still, the server should be stable even if the API is called frequently by automation.

**Decisions & Trade-offs**: By exposing an API, we adhere to the principle of making KireMisu extensible and scriptable. It acknowledges that we can't predict every feature advanced users might want, but we can give them the tools to implement those on their own. The trade-off is the development effort to maintain the API (ensuring consistency, security, etc.) and potential need to support it as the product evolves (every new feature we add might need new endpoints or changes). However, designing the system with an API-first mindset can actually improve the overall architecture (clear separation of front-end and back-end concerns). Since this is a server application at heart, having a well-defined API is natural. We will start with the most critical endpoints and expand as needed, and this will be mentioned as part of our integration strategy (for example, tests can use the API as well, which was hinted in our development plans for testing integration with MangaDex).

## 4. UI/UX Design Priorities

In the previous iteration, UI/UX decisions were made hastily; for KireMisu, we are taking a fresh, user-centered approach to interface design. Although detailed UI mockups will be created in a design tool (like Figma) later, this section outlines the priorities and component layout concepts that will guide that design process. The goal is to ensure the UI supports the functional requirements in an intuitive and attractive way:

**Web-Based App Interface**: KireMisu will be accessed via web browser, presenting a responsive single-page application (SPA) interface. This means users can run the server on a home server or cloud and access it from their PC (or potentially tablet/phone browser). The decision to avoid an Electron-based desktop app ensures better performance and the ability to deploy on headless servers accessible anywhere. The UI will use modern web technologies (e.g. React with a component library such as Shadcn/UI and Tailwind CSS) for a clean, responsive design. (Tech stack specifics aren't finalized here, but we'll use these as guiding examples of the desired modern UI framework.)

**Consistent Modern Design System**: We will adopt a consistent design language (colors, typography, component styles) to give KireMisu a polished look. Using a pre-built component library (like Shadcn or a similar design system) provides accessible and well-tested UI components out of the box, which helps maintain consistency. This ensures things like buttons, modals, forms, and tabs all feel part of one coherent UI. It also accelerates development since we can customize those components rather than designing every element from scratch.

**Intuitive Navigation**: The app's navigation will be structured to accommodate the major sections of functionality without overwhelming the user. Likely, a primary navigation menu will be present (either a sidebar or a top navbar, depending on what works best in layout) with items such as: Library (main collection view), Lists (user-created lists), Watching (watched series management), Search (or integrated search bar), Downloads (queue or list of ongoing downloads from MangaDex), and Settings/Admin. A dashboard or home screen might show an overview (recently added series, maybe the user's progress on various series, watched series updates, etc.) for convenience, especially if the library is large.

### Key UI Components & Layouts

Before diving into visual design, we identify the core screens/components to ensure all use cases are covered:

**Library Browsing View**: A page showing the user's collection of series. This will likely be a grid of manga cover thumbnails with titles, supporting sorting and filtering. Users should be able to toggle between a grid view and list view. In grid mode, covers with maybe series title overlay; in list mode, smaller covers with more details. The filter panel (by tags/genre/status, etc.) can slide out or be an advanced search dialog so casual users see a simple view by default.

**Series Detail Page**: When a user clicks a series, they go to that series' detail page. This shows the cover, the series metadata (description, author, tags, etc.), and a list of chapters/volumes. Chapters might be listed under collapsible volume headers if the series is long. Each chapter entry shows chapter number, title, maybe release date, and an icon if it's been read or downloaded. There should be controls here like "Mark as read/unread", "Download all chapters" (for offline), "Edit Metadata" (which opens a form or modal to edit fields), "Add to Watching" (toggle button for the watching system), and possibly "Add to List" (to put the series in a user list).

**Watching Dashboard Section**: The main dashboard will include a "Watched Series" section showing:
- Series currently being watched with their last update status
- New chapter availability indicators with prominent badges/notifications
- Quick download buttons for new chapters
- Status indicators (last checked, next check time, any errors)

**Watching Management Interface**: A dedicated section for managing watched series:
- List view of all watched series with their watching status and settings
- Options to configure polling frequency per series or globally
- Batch actions for managing multiple watched series
- Import/export watching lists for backup or sharing between instances

**Reader View**: The actual manga reader interface for reading a chapter. This likely takes the full browser window (distraction-free reading mode). It should support different reading modes (single page, two-page spread, vertical scroll for webtoon-style if needed). Navigation controls (next/prev page, next chapter) should be easily accessible, perhaps as an overlay that appears on tap/click or via arrow keys. There should be a toggle for showing/hiding the page thumbnails or a scroll bar for navigation. Crucially, the reader view will have an option for adding an annotation or viewing notes: e.g., a button that opens a small sidebar or modal where the user can type a note for that chapter. If a note exists, the icon could indicate so (highlighted or numbered). The design should ensure that adding a note doesn't disrupt reading – maybe it pauses on the current page and allows the note. Users should also be able to exit the reader easily to return to the series page or library.

**Lists/Collections Page**: A section where user-defined lists are managed. Possibly the navigation has a "Lists" item that opens a page listing all custom lists (and maybe some default smart filters like "All", "Unread", etc.). Each list, when clicked, shows series under that list (similar to the library view but filtered to that list). There should be an option to create a new list, rename or delete a list, and maybe ordering of lists. This page basically helps organize custom groupings.

**Search & Discovery UI**: A unified search bar at the top might allow the user to search their library. If we integrate MangaDex search here, the UI might show something like "Local results" vs "MangaDex results" tabs. Alternatively, a dedicated "Add from MangaDex" flow: clicking an "Add Series" button could prompt whether to add from local path or search online. For the MangaDex search results, the UI should clearly differentiate content not yet in the library (and allow one-click adding/downloading). If a series is found online, the user might see an option to import it (metadata only or with chapters). This process should be straightforward so casual users can grab new series easily.

**Downloads/Queue**: If the user initiates downloads (from MangaDex), an indicator or page should show active downloads, progress, and completed downloads. Perhaps an icon in the header (like a down-arrow or tray) that when clicked shows a dropdown or page of current downloads. This way, the user knows when background downloads (like a whole volume) are finished.

**Notification System**: A notification system within the UI:
- Header notification indicator showing count of new chapters available
- Notification panel/dropdown showing recent updates from watched series
- Dismissible notifications with action buttons (download, mark as seen)
- Optional browser notifications (when supported and permitted)

**Settings/Admin Panel**: A section for configuration and advanced management. Here, a tech-savvy user can set up library paths (add/edit/remove the directories the app scans), view storage status, configure their naming scheme for renaming, manage the API key (generate/regenerate), configure watching system settings (polling intervals, notification preferences), and set preferences (like enabling beta features, adjusting sync intervals, etc.). Also, account settings like changing the password for login (and eventually managing user accounts if multi-user in future) would be here. The settings area might be hidden from casual users (or collapsed) to avoid confusion – it's mainly for the owner/admin of the server. Clear organization and help text in this area will be important given the complexity of some settings (e.g., regex for naming conventions).

**Responsive Design (Future-Facing)**: Initially, KireMisu's UI will be optimized for desktop/web usage since a lot of self-hosters and readers use PCs or laptops. However, we will keep responsive design principles in mind – ensuring the layout can adjust to different screen sizes. For example, the grid view could re-flow for tablets, and perhaps a minimal mobile view could let one read or check their list in a pinch. Full mobile app support is out of scope for v1, but by using flexible web components and common frameworks, we keep the door open to either a Progressive Web App or a dedicated mobile app down the line.

**Visual Priorities**: The interface should emphasize cover art and manga imagery (since manga is a visual medium) – hence the library grid of covers, large cover on series page, etc. Text (titles, metadata) should be clean and secondary to the images, but easily readable. The design will offer both light and dark theme modes, if possible, since many readers prefer dark mode for reading comfort. Performance considerations for UI include using cached thumbnails and low-resolution previews where appropriate to avoid loading large images unnecessarily. The watching system features will be visually distinguished with clear indicators for watched status, new content availability, and system health. The app should feel snappy: using async loads and skeleton screens to load content will prevent the interface from feeling sluggish even as it pulls data from disk or the internet.

Overall, the UI/UX philosophy is "simple on the surface, powerful underneath." A new user can easily browse and read without configuring anything complex, while an advanced user can delve into filters, tags, watching settings, and other advanced features to tailor the experience. We will iterate on the UI with user feedback (even if the "user" initially is the creator themselves) to refine practicality – ensuring that the mistakes of impractical UX from the first pass are avoided. Wireframes and prototypes will be developed (in Figma or similar) to test these layouts before full implementation, guided by the components and priorities listed above.

## 5. Non-Functional Requirements

In addition to the user-facing features, KireMisu's design must satisfy several non-functional requirements to ensure the system is reliable, scalable (to a point), and maintainable in a self-hosted environment:

**Authentication & Security**: Initially, KireMisu will support a basic username/password login system to restrict access to the library (important if the server is hosted on the cloud or a home network). Since multi-user support is not in the first version, one set of credentials (or one admin user) will suffice for access. Passwords will be stored securely (hashed). In future, integration with OAuth or external auth providers can be added, especially if multi-user is introduced. All network communication, especially the login and API, should be secured via HTTPS/SSL (though this is often handled by the deployment environment or a reverse proxy like Traefik or Nginx in front of the app). The application should also implement basic security best practices (sanitize inputs, prevent SQL/NoSQL injection, use secure headers, etc.) given it might be exposed to the internet.

**Performance & Scalability**: KireMisu is designed to perform well for a personal library. It should handle moderately large collections (thousands of series or tens of thousands of chapters) with responsive UI and reasonable memory/CPU usage. Using indexing in the database and caching of images/metadata will aid performance. For scalability, the app will run as a stateless web server with the database and storage as external dependencies, making it relatively easy to scale vertically (more resources on one machine) or even horizontally (multiple instances) if needed. However, active-active high availability (multiple instances concurrently) is not an immediate requirement for v1, since one instance should suffice for a single user. We will design with a cloud-native mindset (stateless app, externalize state to DB and storage) so that adding HA later or scaling out is possible without a complete rewrite. For instance, if demand arises, one could run multiple app containers behind a load balancer, as long as they share the same database and storage – the app should function in that scenario with minimal tweaks.

**Database & Data Integrity**: A robust database backend will be used to store metadata, user data (like lists, annotations, account info), watching status and history, and app settings. Rather than using a simple file-based DB like SQLite (which can be prone to corruption under concurrent access or large data), we prefer a more resilient solution. Options include a document-oriented database like MongoDB or CouchDB (as initially considered) or an SQL database (PostgreSQL/MySQL) with an ORM that allows flexible JSON fields for metadata. The key is that the DB should handle flexible schema (to easily add new metadata fields or features) and be reliable in a long-running server context. The app will include migration tools or use an ORM/migration framework to update the schema as the product evolves. Regular backups of the database should be encouraged (perhaps provide an export tool or at least document the procedure) to protect user data like reading progress and notes. Also, any long binary data (like images) might be stored on disk or object storage rather than in the DB to keep the database lean – e.g., cover images can be stored as files or base64 strings in a store, while their paths or references are in the DB.

**Storage Management & Durability**: The manga files are stored on the user's own storage (NAS, disk, etc.), as described in Media Management. The system will not alter or delete files without user action, which protects the actual media. We assume the user takes responsibility for the durability of this storage (e.g., using a RAID NAS or backing up their files). That said, KireMisu should behave gracefully if files disappear or disk is slow/unavailable – e.g., if a network drive goes offline, the app should show errors for those items but not crash entirely. Re-sync and error handling in these scenarios will be considered (perhaps marking series as temporarily unavailable).

**Deployment & DevOps**: KireMisu will be delivered as a containerized application for ease of deployment. Providing a Docker image (and a Docker Compose example for those who want a quick start) is a priority. This allows users to run the server with minimal setup on any platform that supports Docker. For more advanced users, Kubernetes deployment manifests (Helm chart or Kustomize files) will be made available, aligning with the initial project vision of using K3s and ArgoCD for GitOps deployments. While not all users will use Kubernetes, having that option and documentation means KireMisu fits well into cloud-native stacks. Continuous Integration/Continuous Deployment (CI/CD) will be set up (for example, using GitHub Actions as planned) so that tests run on each commit and Docker images can be auto-built and versioned. This ensures that even as the sole developer (at the start), the project maintains good practices for quality and reliability.

**Testing & Quality Assurance**: The system will be developed alongside a comprehensive test suite. Unit tests will cover the core logic (e.g., parsing metadata, renaming functions, API endpoints, watching system polling), and integration tests will simulate workflows (like adding a series, syncing metadata, reading progress updates, watching notifications). Using mock data (e.g., dummy MangaDex API responses or fake file structures) will ensure tests don't depend on external services or actual large files. The emphasis on testing (which was in the original plan) increases confidence that adding new features (or refactoring) won't break existing functionality. This is particularly important given the multiple features (files, network calls, UI, etc.) – a robust test suite catches issues early.

**Documentation & Support**: Clear documentation will be provided for both end-users and developers. This includes a README or user guide explaining how to deploy KireMisu (covering prerequisites like Docker, how to mount volumes, how to configure environment variables for DB connections, etc.), how to use the application's features, and troubleshooting common issues. Since our target users include server admins who love tinkering, good documentation is crucial to adoption. Developer-oriented docs (for those wanting to contribute or just understand the architecture) will also be included, outlining the design and any notable patterns. This was highlighted in the project's Phase 0 user stories (like providing example K3s manifests and Docker compose files with instructions), and remains a priority to ensure anyone (including "future me") can set up and run the system with minimal friction.

In summary, the non-functional aspects ensure that KireMisu is secure, performant, and maintainable in a self-hosted context. By using cloud-native principles (containerization, externalized state) and avoiding fragile setups (like single-file DBs that risk corruption), we aim for a system that can run 24/7 on a home server or cloud VM reliably. The initial focus is on making it robust for one primary user, but with foresight toward scaling and expanding to more users or more complex deployments when the time comes. We prefer making conservative technology choices now (proven databases, standard frameworks) over experimental ones, to avoid derailing development – the lesson from the earlier attempt is to keep the tech grounded in what serves the product's requirements best, rather than tech for tech's sake.

## 6. Assumptions & Constraints

This section lists key assumptions and constraints considered while defining KireMisu's requirements, to clarify the context in which the product will operate:

**Self-Hosted Environment**: It's assumed the user will deploy KireMisu on their own server or machine. This could range from a NAS, a home lab server, to a VPS or cloud instance. The user should have the capability to run Docker containers (or Node/whatever runtime if running without Docker). We assume users have at least basic technical knowledge to set up the environment (since target is self-hosters). This is not a managed cloud service – the user is responsible for hosting.

**Single User/Admin Initially**: We assume only one primary user (or a small trusted group) will be using the system in initial release. There is no complex role-based access control or separate user libraries at launch. This simplifies design (no need for extensive permission handling) but means the product is less suited for a scenario like a large shared server with many strangers. We assume the single user is the admin as well, who can access settings and perform all actions.

**Content Responsibility**: The application itself doesn't provide content beyond integration with MangaDex. It's assumed the user has or will obtain manga content either by adding their own files or using the MangaDex search/download feature within allowed usage. Any licensing or rights issues of content are outside the scope of the software – the user is responsible for what they add to their library. (This is a typical assumption to clarify that KireMisu is a tool, not a content provider, except through official APIs like MangaDex.)

**Storage and Network**: We assume the user has sufficient storage for their manga collection and a relatively stable network (especially if using MangaDex integration or remote access). Large file transfers (like downloading many chapters, or streaming images to the browser) will require decent bandwidth, so the experience may vary with network quality. If the user's server is low-power (like a Raspberry Pi), performance may be constrained – but basic functionality should still work albeit slower (we won't design exclusively for high-end hardware).

**Kubernetes/Container Orchestration (Optional)**: While KireMisu can run as a single Docker container, an assumption (from the initial project) is that some users might run it on Kubernetes or similar. We consider this in our configuration (for example, using environment variables or config files for all settings, not requiring any GUI setup steps that can't be done in an automated deploy). We also assume the runtime environment could be ephemeral, so persistent data (DB, user files) must be stored in external volumes or databases.

**External Services**: The main external dependency is the MangaDex API. We assume this service remains available and free to use within reasonable limits. If MangaDex changes terms or API drastically, it could constrain our integration. We design with the assumption that using their API for metadata and some downloads is acceptable usage. If not, alternative solutions or scrapers might be needed (outside scope for now).

**No Real-time Collaboration Needs**: Since it's single-user, we don't consider issues like two people editing the same thing at once. This simplifies concurrency concerns (the app mostly just needs to handle its own asynchronous tasks).

**Data Size Constraints**: We assume individual manga files (like chapters in .cbz or .pdf) are not absurdly large (most are tens of MBs, maybe up to 100s of MB for some). The app can handle these sizes in memory/transfer. We won't initially optimize for extremely large files like multi-gigabyte PDFs, as that's not typical for manga. Similarly, the total number of items, while potentially thousands, is still in a range that a single server and database can handle (with indexing).

These assumptions will be revisited as needed. Recognizing them helps to define the scope and ensure we don't over-engineer features that aren't necessary for the expected context. It also helps identify potential constraints early – for example, the dependency on MangaDex is a constraint that we manage via caching and graceful failure modes. The constraint of a self-hosted environment means we provide more setup docs than a typical consumer app might. All in all, these factors frame how KireMisu is built and who it is built for.

## 7. Future Expansion Opportunities

Looking beyond the initial release of KireMisu, there are several enhancements and expansions that are out of scope for now but planned for the future. Keeping these in mind during design will ensure the architecture can accommodate them when the time comes:

**Multi-User Support**: Introduce robust multi-user capabilities so that multiple people can have profiles or accounts on the same KireMisu instance. This involves user-specific reading progress, personal lists, personal watching lists, and possibly content restrictions. It would require more advanced authentication (possibly OAuth/OpenID integration as originally envisioned) and role management (admin vs standard user). While not needed for the creator's personal use initially, this feature would broaden the appeal of KireMisu for families or small communities who might share a server.

**Mobile Applications & Responsive Enhancements**: Develop a dedicated mobile app (or a polished Progressive Web App) for KireMisu to provide a first-class reading experience on smartphones and tablets. This could leverage the existing public API. A mobile app could allow offline syncing of content (download manga to the device for offline reading, with two-way sync of progress when back online). Even without a native app, making the web interface fully responsive (beyond the basics) is a goal – including touch-friendly reader UI improvements and perhaps an option to cache certain data offline via the browser.

**Enhanced Offline Mode**: Building on the initial offline features, future versions could support an "offline mode" where a user can mark certain series for offline access and the app can package those chapters for download in bulk, or even an automated sync to a device. This overlaps with a mobile app idea, but even for the web app, one could imagine exporting a portable HTML/CBZ bundle of a reading list, etc. The key is to expand the convenience of offline reading beyond the basic file export of v1.

**Additional Content Sources**: Integrate more manga content sources or repositories beyond MangaDex. This could include other public APIs, compatibility with other self-hosted solutions (for example, reading from a Komga server or Jellyfin library), or even the ability to scrape certain websites if allowed. A plugin system might be introduced so that community-developed connectors can feed content or metadata from various sites. The watching system would extend to support multiple sources with unified notifications.

**Community and Social Features**: Though far out, features like allowing users to rate or review series within their library, or share their lists (maybe export a list of titles or a OPDS catalog for others to see) could be interesting. If multi-user arrives, perhaps a shared "community" within an instance (like commenting on a series). These are not core to the personal use-case but could evolve as the project grows.

**High Availability & Scalability**: If KireMisu were to be deployed in larger contexts or if it becomes popular, we might look at clustering the application for high availability – e.g., running multiple instances behind a load balancer connected to a distributed database. Our initial cloud-native approach keeps this door open (stateless app servers, external DB). Future optimization might include caching layers or splitting services (maybe a microservice for the image server, etc.) to handle very large libraries or many concurrent users.

**UI/UX Refinements with New Tech**: Continuously update the interface by incorporating new design trends or technologies (for example, if a new web component library supersedes Shadcn, or using capabilities like WebAssembly for performance in image decoding, etc.). Also, possibly introducing themes or more customization in the UI (letting users choose layout densities, custom cover sizes, etc.).

**Analytics (Local) and Insights**: Provide the user with insights into their reading habits or library (all locally, respecting privacy since this is self-hosted). For example, stats like "manga read this month" or "most read genres". This could be a fun addition down the line using the data the app already has.

Each of these future items will be explored once the core product is stable and fulfilling its primary goals. By listing them, we ensure that KireMisu's initial architecture doesn't unintentionally block these directions. The development approach will be iterative – after launching the MVP (Minimum Viable Product) covering the core features in this PRD, feedback will guide which of these expansions to prioritize. The overarching theme is that KireMisu is a living project that can grow from a personal tool into a richer platform, all while staying true to the idea of giving manga lovers full control over their reading experience.
