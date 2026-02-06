# Scraper Core Capability Specification (Delta)

## MODIFIED Requirements

### Requirement: BossScraper initialization
The BossScraper class SHALL support multiple browser initialization strategies with automatic fallback and enhanced error handling.

#### Scenario: Initialize with auto-launch enabled
- **WHEN** BossScraper is instantiated with BROWSER_AUTO_LAUNCH=true
- **THEN** the system SHALL first attempt to connect to an existing browser on the configured port
- **AND** if no browser is detected, the system SHALL launch a new browser instance
- **AND** the system SHALL initialize the ChromiumPage with the connected/launched browser
- **AND** the system SHALL log the initialization method used

#### Scenario: Initialize with auto-launch disabled
- **WHEN** BossScraper is instantiated with BROWSER_AUTO_LAUNCH=false
- **THEN** the system SHALL attempt to connect to an existing browser on the configured port
- **AND** if no browser is detected, the system SHALL raise an exception
- **AND** the exception message SHALL instruct the user to start a browser manually with the correct debug port

#### Scenario: Initialize with headless mode
- **WHEN** BossScraper is instantiated with BROWSER_HEADLESS=true
- **THEN** the system SHALL configure ChromeOptions with headless flag
- **AND** the browser SHALL launch without visible UI
- **AND** all scraping operations SHALL function normally

#### Scenario: Initialization fails completely
- **WHEN** both connection and launch attempts fail
- **THEN** the system SHALL raise an exception with detailed error information
- **AND** the error message SHALL include the reason for failure
- **AND** the error message SHALL suggest troubleshooting steps

### Requirement: ChromiumOptions configuration
The system SHALL configure ChromiumOptions based on environment settings and support multiple configuration options.

#### Scenario: Default configuration
- **WHEN** BossScraper is instantiated with default settings
- **THEN** the system SHALL set the remote debugging port from Config.CHROME_PORT
- **AND** the system SHALL apply default Chrome options for stability

#### Scenario: Custom executable path
- **WHEN** BROWSER_EXECUTABLE_PATH is configured
- **THEN** the system SHALL set the browser executable path in ChromiumOptions
- **AND** the system SHALL verify the executable exists before use

#### Scenario: Headless configuration
- **WHEN** BROWSER_HEADLESS is set to true
- **THEN** the system SHALL add the '--headless' argument to ChromiumOptions
- **AND** the system SHALL add '--disable-gpu' argument for compatibility
- **AND** the system SHALL add '--no-sandbox' argument for server environments

### Requirement: Browser lifecycle management
The BossScraper class SHALL properly manage browser lifecycle based on how the browser was initialized.

#### Scenario: Cleanup auto-launched browser
- **WHEN** BossScraper instance is destroyed and the browser was auto-launched
- **THEN** the system SHALL close the browser instance
- **AND** the system SHALL release all system resources

#### Scenario: Preserve existing browser
- **WHEN** BossScraper instance is destroyed and connected to an existing browser
- **THEN** the system SHALL NOT close the browser
- **AND** the browser SHALL remain available for other connections

#### Scenario: Cleanup on exception
- **WHEN** an exception occurs during initialization
- **THEN** the system SHALL clean up any partial browser resources
- **AND** the system SHALL log the cleanup action

## REMOVED Requirements

### Requirement: Remote debugging port only configuration
**Reason**: Replaced by flexible browser initialization strategy that supports both connecting and launching

**Migration**: Existing code that relies on manually starting Chrome with `--remote-debugging-port=9222` will continue to work. The system now additionally supports auto-launching the browser when not already running. No migration required - the feature is backward compatible.

## ADDED Requirements

### Requirement: Browser availability detection
The system SHALL detect if a browser is available on the configured debug port before attempting connection.

#### Scenario: Browser is available
- **WHEN** a browser is listening on the configured debug port
- **THEN** the system SHALL detect the browser availability
- **AND** the system SHALL proceed with connection

#### Scenario: Browser is not available
- **WHEN** no browser is listening on the configured debug port
- **THEN** the system SHALL detect that no browser is available
- **AND** the system SHALL proceed with launch or error based on BROWSER_AUTO_LAUNCH setting

### Requirement: Initialization method tracking
The system SHALL track how the browser was initialized to control cleanup behavior.

#### Scenario: Track auto-launched browser
- **WHEN** the system launches a new browser instance
- **THEN** the system SHALL mark the browser as auto-launched
- **AND** the system SHALL use this flag during cleanup to close the browser

#### Scenario: Track connected browser
- **WHEN** the system connects to an existing browser
- **THEN** the system SHALL mark the browser as externally managed
- **AND** the system SHALL use this flag during cleanup to preserve the browser
