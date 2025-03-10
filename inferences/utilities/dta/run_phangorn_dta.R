#!/usr/bin/env Rscript

# Load required libraries
library(ape)
library(dplyr)
library(phangorn)
library(optparse)

# Define command-line arguments
option_list <- list(
  make_option(
    c("-t", "--tree"),
    type = "character",
    help = "Input Newick tree file (non-annotated)",
    metavar = "file"),
  make_option(
    c("-a", "--attributes"),
    type = "character",
    help = "Input annotation TSV file",
    metavar = "file"),
  make_option(
    c("-c", "--column"),
    type = "character",
    default = "deme",
    help = "Column name for the relevant node attribute (default: 'deme')",
    metavar = "column")
)

# Parse command-line arguments
opt <- parse_args(OptionParser(option_list = option_list))

# Check if required arguments are provided
if (is.null(opt$tree) || is.null(opt$attributes)) {
  stop(
    "Please provide all required arguments: ",
    "--tree and --attributes."
  )
}

# Read tree and attributes
tree <- read.tree(opt$tree)
attributes <- read.table(opt$attributes, header = TRUE, sep = "\t")

# Ensure the specified column exists in the attributes file
if (!(opt$column %in% colnames(attributes))) {
  stop(
    paste("The specified column",
    opt$column,
    "does not exist in the attributes file."))
}

# Create a named vector of tip states using the specified column
tip_states <- setNames(attributes[[opt$column]], attributes$name)

# Convert to phyDat format
phy_dat <- phyDat(
  as.list(tip_states),
  type = "USER",
  levels = unique(tip_states))

# Perform ancestral state reconstruction
pars_result <- ancestral.pars(tree, phy_dat)

# Precompute unique tip states
unique_states <- unique(tip_states)

# Map the reconstructed states
mapped_states <- lapply(pars_result, function(inferred_states) {
  inferred_index <- which(inferred_states == 1)  # Find indices where value is 1
  unique_states[inferred_index]                 # Map to corresponding states
})

# Write the output to stdout
output_data <- data.frame(
  name = names(mapped_states),
  deme = sapply(
    mapped_states,
    function(states) paste(states, collapse = ", "))
)
write.table(
  output_data,
  file = stdout(),  # Output to stdout
  sep = "\t",
  row.names = FALSE,
  col.names = FALSE,
  quote = FALSE)

cat("Node-state mapping completed.\n", file = stderr())  # Status to stderr