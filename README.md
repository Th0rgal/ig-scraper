<div align="center">

# 📸 Instagram Profile Scraper

![Python](https://img.shields.io/badge/python-v3.7+-blue.svg)
![Selenium](https://img.shields.io/badge/selenium-4.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-windows-lightgrey.svg)

_A fast and efficient Instagram profile scraper that extracts public post data without authentication_

</div>

## 🎯 Problem Statement

Instagram's web interface makes it challenging to programmatically extract public profile data for research, analysis, or personal archiving purposes. Many existing solutions require authentication, violate terms of service, or are unreliable due to frequent UI changes.

## ✨ Solution

This project provides a robust Instagram scraper that:

-   Extracts data from public Instagram profiles without requiring login credentials
-   Retrieves image URLs and captions from the latest posts
-   Outputs structured JSON data for easy processing
-   Supports proxy rotation for enhanced reliability
-   Complies with Instagram's terms of service by only accessing publicly available data

## ⚠️ Important Notice

> **Proxy Stability Warning**: This project uses publicly available free proxies which may not always be stable or functional. For production use or consistent performance, we recommend using your own IP address or premium proxy services.

## 🚀 Features

-   **No Authentication Required**: Scrapes public data without login credentials
-   **Dual Mode Operation**: Standard scraping and proxy-enabled scraping
-   **JSON Output**: Clean, structured data export
-   **Error Handling**: Robust error handling and timeout management
-   **User Agent Rotation**: Mimics real browser behavior
-   **Proxy Support**: Built-in proxy rotation for enhanced reliability

## 📋 Requirements

-   Python 3.7+
-   Chrome browser installed
-   ChromeDriver (included in project)
-   Windows OS (current setup)

## 🛠️ Setup

1. **Clone the repository**

    ```bash
    git clone https://github.com/mr-teslaa/instagram_user_post_scraper
    cd instagram-_user_post_scraper
    ```

2. **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

3. **Verify ChromeDriver**

    - ChromeDriver is included in the `chromedriver-win64` folder
    - Ensure Chrome browser is installed on your system

4. **Setup proxies (optional)**
    - Add proxy addresses to `proxy.txt` file (format: `ip:port`)
    - One proxy per line

## 💻 Usage

### Basic Scraping (No Proxy)

```bash
python insta_spider.py
```

### Proxy-Enabled Scraping

> **⚠️ Proxy Stability Warning**: This project uses publicly available free proxies which may not always be stable or functional. For production use or consistent performance, we recommend using your own IP address or premium proxy services.

```bash
python insta_spider_proxy.py
```

Both scripts will prompt you to enter an Instagram username and will output the scraped data in JSON format.

### Example Output

```json
{
	"username": "example_user",
	"total_posts": 12,
	"posts": [
		{
			"img_src": "https://instagram.com/image1.jpg",
			"img_caption": "Sample caption text"
		},
        .....
	]
}
```

📄 **[View Sample Output](output.json)** - See real scraped data from our testing

## 📁 Project Structure

```
instagram-scraper/
├── insta_spider.py          # Basic scraper without proxy
├── insta_spider_proxy.py    # Proxy-enabled scraper
├── requirements.txt         # Python dependencies
├── proxy.txt               # Proxy list (optional)
├── output.json             # Sample output file
├── chromedriver-win64/     # ChromeDriver executable
└── README.md               # This file
```

## ⚖️ Legal Compliance

This scraper:

-   Only accesses publicly available data
-   Does not use authentication or session keys
-   Respects Instagram's robots.txt
-   Implements reasonable delays between requests
-   Does not store or redistribute Instagram's copyrighted content

Users are responsible for ensuring their usage complies with Instagram's Terms of Service and applicable laws.

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

### Areas for Contribution

-   Improve proxy handling and rotation
-   Add support for other platforms (Linux, macOS)
-   Enhance error handling and retry mechanisms
-   Add data export formats (CSV, XML)
-   Implement rate limiting features
-   Add unit tests and documentation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⭐ Show Your Support

If this project helped you, please give it a ⭐! It helps others discover the project and motivates continued development.

## 🔧 Troubleshooting

**Common Issues:**

-   **Could not access profile**: Most common issue, it's becuase instagram use rate limit to prevent unwanted bot, so wait for couple of minute and try again or use private proxy.
-   **ChromeDriver not found**: Ensure the path in the script matches your ChromeDriver location
-   **Proxy not working**: Try different proxies from your `proxy.txt` file
-   **Profile not loading**: Some profiles may require different wait times or have restricted access
-   **Empty results**: The profile might be private or have no posts

**Need Help?** Open an issue with:

-   Your operating system
-   Python version
-   Error message (if any)
-   Steps to reproduce the problem

---

<div align="center">

**Made with ❤️ by Hossain Foysal for the developer community | Portfolio: https://HossainFoysal.com**

_Remember to star ⭐ this repo if you found it useful!_

</div>
