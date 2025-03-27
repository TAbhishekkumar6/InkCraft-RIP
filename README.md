# InkCraft RIP Software

A free and open-source Direct-to-Garment (DTG) Raster Image Processor (RIP) software for Epson F2100 and F2130 printers.

## Project Overview

This project aims to create a feature-rich alternative to commercial DTG RIP software like Kothari Print Pro, with an advanced user interface and comprehensive support for Epson DTG printers.

## Development Phases

### Phase 1: Reverse-Engineering Epson Print Driver (Current)
- Capture printer communication via USB sniffing
- Analyze ESC/POS or ESC/P2 commands
- Test custom commands directly to the printer
- Develop a basic driver package

### Phase 2: Core RIP Engine Development (Upcoming)
- Image processing and color management
- Halftone processing
- White underbase generation
- Ink control and optimization

### Phase 3: User Interface Development (Upcoming)
- Modern UI with intuitive workflow
- Print queue management
- Job costing and estimation
- Design preview and adjustment tools

## Getting Started

### Prerequisites
- Windows 10/11
- USB connection to compatible Epson printer
- Python 3.8+ (for development)
- Wireshark with USBPcap for USB analysis

### Installation
*Installation instructions will be provided once the project reaches beta stage*

## Contributing
We welcome contributions from the community! Whether you're fixing bugs, adding new features, improving documentation, or spreading the word - we'd love to have you as part of the project.

Please check our [Contributing Guidelines](../CONTRIBUTING.md) for details on:
- How to get started
- Development workflow
- Bug reporting
- Feature requests
- Coding standards
- Pull request process

## License
This project is licensed under the [GPL v3](LICENSE)

## Disclaimer
This software is not affiliated with or endorsed by Epson or Kothari. It is an independent project aimed at providing an open-source alternative for DTG printing. 