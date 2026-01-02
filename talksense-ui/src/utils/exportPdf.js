
import html2canvas from "html2canvas";
import jsPDF from "jspdf";

export async function exportPDF(ref) {
    const element = ref.current;
    if (!element) return;

    try {
        const canvas = await html2canvas(element, {
            scale: 2,
            useCORS: true,
            backgroundColor: "#ffffff",
            logging: false,
            onclone: (clonedDoc) => {
                // Optional: Hide specific elements in the clone if needed via class name
                const noPrint = clonedDoc.getElementsByClassName("no-print");
                for (let i = 0; i < noPrint.length; i++) {
                    noPrint[i].style.display = "none";
                }
            }
        });

        const imgData = canvas.toDataURL("image/png");
        const pdf = new jsPDF("p", "mm", "a4");

        const pageWidth = pdf.internal.pageSize.getWidth();
        const pageHeight = pdf.internal.pageSize.getHeight();

        const imgWidth = pageWidth;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;

        let position = 0;
        let heightLeft = imgHeight;

        pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;

        while (heightLeft > 0) {
            position -= pageHeight;
            pdf.addPage();
            pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;
        }

        pdf.save("TalkSense_Analysis_Report.pdf");
    } catch (error) {
        console.error("PDF Generation failed:", error);
        alert("Failed to generate PDF. Please try again.");
    }
}
