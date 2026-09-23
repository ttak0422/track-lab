//! PDF-only bridge. The caller owns deadlines, original retention and output files.

use std::{error::Error, io};
use xberg::{ExtractInput, ExtractionConfig, PageConfig, PdfConfig, PostProcessorConfig};

fn run() -> Result<(), Box<dyn Error>> {
    let mut args = std::env::args_os().skip(1);
    let path = args.next().ok_or("usage: track-pdf-engine input.pdf")?;
    if args.next().is_some() {
        return Err("usage: track-pdf-engine input.pdf".into());
    }
    let bytes = std::fs::read(path)?;
    if !bytes.starts_with(b"%PDF-") {
        return Err("input does not have a PDF header".into());
    }
    // No config discovery, OCR fallback, model downloads, cache or text rewriting.
    let config = ExtractionConfig {
        use_cache: false,
        enable_quality_processing: false,
        disable_ocr: true,
        pages: Some(PageConfig {
            extract_pages: true,
            ..Default::default()
        }),
        pdf_options: Some(PdfConfig {
            extract_tables: false,
            extract_form_fields: false,
            ..Default::default()
        }),
        postprocessor: Some(PostProcessorConfig {
            enabled: false,
            ..Default::default()
        }),
        ..Default::default()
    };
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()?;
    let result = runtime.block_on(xberg::extract(
        ExtractInput::from_bytes(bytes, "application/pdf", None),
        &config,
    ))?;
    if !result.errors.is_empty() || result.results.len() != 1 {
        return Err(format!("PDF extraction failed: {:?}", result.errors).into());
    }
    let document = &result.results[0];
    if document.metadata.error.is_some() || document.metadata.ocr_used {
        return Err("PDF extraction returned an error or unexpected OCR output".into());
    }
    let page_count = document
        .metadata
        .pages
        .as_ref()
        .ok_or("missing PDF page count")?
        .total_count;
    serde_json::to_writer(
        io::stdout().lock(),
        &serde_json::json!({
            "engine": "xberg 1.2.6 (native)",
            "page_count": page_count,
            "pages": document.pages,
            "warnings": document.processing_warnings,
        }),
    )?;
    Ok(())
}

fn main() -> std::process::ExitCode {
    match run() {
        Ok(()) => std::process::ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("{error}");
            std::process::ExitCode::FAILURE
        }
    }
}
