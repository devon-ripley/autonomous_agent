#!/usr/bin/env python3
"""
Web Search and Browsing Tool.
Allows the agent to search Google and read web pages.
"""
import argparse
import sys
import requests
from bs4 import BeautifulSoup
from googlesearch import search

def google_search(query, num_results=5):
    """Perform a Google search."""
    print(f"Searching for: {query}")
    try:
        results = []
        for j, result in enumerate(search(query, num_results=num_results, advanced=True)):
            results.append(f"{j+1}. {result.title}\n   URL: {result.url}\n   Snippet: {result.description}")
        return "\n\n".join(results)
    except Exception as e:
        return f"Search failed: {e}"

def read_url(url):
    """Fetch and parse text from a URL."""
    print(f"Reading: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:5000] + "\n...[Truncated]" if len(text) > 5000 else text
        
    except Exception as e:
        return f"Failed to read URL: {e}"

def main():
    parser = argparse.ArgumentParser(description="Web Search and Browsing Tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", "-q", help="Search query")
    group.add_argument("--url", "-u", help="URL to read")
    
    args = parser.parse_args()
    
    if args.query:
        print(google_search(args.query))
    elif args.url:
        print(read_url(args.url))

if __name__ == "__main__":
    main()
