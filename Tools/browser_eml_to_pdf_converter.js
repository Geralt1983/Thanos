// Google Drive EML to PDF Converter
async function convertEmlToPdf() {
    // Authenticate and access Google Drive
    await page.goto('https://drive.google.com/drive/my-drive');
    
    // Wait for login if needed
    try {
        await page.waitForSelector('input[type="email"]', { timeout: 5000 });
        await page.type('input[type="email"]', 'jkimble1983@gmail.com');
        await page.click('#identifierNext');
        
        // Wait for password
        await page.waitForSelector('input[type="password"]', { timeout: 5000 });
        await page.type('input[type="password"]', 'YOUR_PASSWORD');
        await page.click('#passwordNext');
        
        // Wait for Drive to load
        await page.waitForNavigation();
    } catch (e) {
        console.log('Already logged in or login not required');
    }
    
    // Navigate to Work Docs folder
    await page.goto('https://drive.google.com/drive/folders/1hT5ZXqK9QkGwWAelkrFR4VSTRVgmH3fs');
    
    // Wait for folder contents
    await page.waitForSelector('[role="listitem"]');
    
    // Create output folder
    await page.goto('https://drive.google.com/drive/folders/1_HGSfGQWHuDQmNAYqhb8XYZ123456789');
    await page.waitForSelector('div[role="button"]:has-text("New")');
    
    // Function to convert EML to PDF
    async function convertEmlFile(fileElement) {
        // Open file details
        await fileElement.click();
        await page.waitForSelector('div[role="dialog"]');
        
        // Download EML
        const downloadButton = await page.$('div[role="button"]:has-text("Download")');
        await downloadButton.click();
        
        // Wait for download
        const downloadPath = await page._client.send('Page.setDownloadBehavior', {
            behavior: 'allow',
            downloadPath: '/tmp/eml_downloads'
        });
        
        // Convert EML to PDF (client-side)
        const pdfPath = await page.evaluate(async (emlPath) => {
            const { PDFDocument } = await import('https://cdn.jsdelivr.net/npm/pdf-lib/dist/pdf-lib.min.js');
            const { readFile } = await import('fs/promises');
            
            // Read EML file
            const emlContent = await readFile(emlPath, 'utf8');
            
            // Create PDF
            const pdfDoc = await PDFDocument.create();
            const page = pdfDoc.addPage();
            const { width, height } = page.getSize();
            const fontSize = 12;
            
            page.drawText(emlContent, {
                x: 50,
                y: height - 4 * fontSize,
                size: fontSize
            });
            
            // Save PDF
            const pdfBytes = await pdfDoc.save();
            await writeFile('/tmp/eml_downloads/converted.pdf', pdfBytes);
            
            return '/tmp/eml_downloads/converted.pdf';
        }, downloadPath);
        
        // Upload PDF to output folder
        const uploadButton = await page.$('div[role="button"]:has-text("New")');
        await uploadButton.click();
        
        const fileInput = await page.$('input[type="file"]');
        await fileInput.setInputFiles(pdfPath);
        
        // Wait for upload
        await page.waitForSelector('div:has-text("Upload complete")');
    }
    
    // Find and convert EML files
    const emlFiles = await page.$$('[role="listitem"]:has-text(".eml")');
    for (const file of emlFiles) {
        await convertEmlFile(file);
    }
}

// Run the conversion
convertEmlToPdf();