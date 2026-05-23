// dicom.go
// DICOM header parsing module — AcmeDevice v2.1

package dicom

import (
	"errors"
	"fmt"
)

// MandatoryTags defines required DICOM header fields per IEC 62304 traceability
var MandatoryTags = []string{
	"0008,0060", // Modality
	"0010,0020", // Patient ID
	"0008,0020", // Study Date
	"0008,103E", // Series Description
}

// DicomHeader represents parsed DICOM metadata
type DicomHeader struct {
	Tags map[string]string
}

// @req SR-003 @risk RISK-004 @class B @mitigation MIT-004
func ValidateHeader(header *DicomHeader) error {
	if header == nil {
		return errors.New("nil DICOM header")
	}

	for _, tag := range MandatoryTags {
		val, ok := header.Tags[tag]
		if !ok || val == "" {
			return fmt.Errorf("mandatory DICOM tag %s missing or empty", tag)
		}
	}

	return nil
}

// @req SR-003 @class B
func ParseHeader(data []byte) (*DicomHeader, error) {
	if len(data) < 132 {
		return nil, fmt.Errorf("data too short for valid DICOM: %d bytes", len(data))
	}

	// Verify DICOM magic bytes at offset 128
	if string(data[128:132]) != "DICM" {
		return nil, errors.New("invalid DICOM preamble: missing DICM magic")
	}

	header := &DicomHeader{Tags: make(map[string]string)}
	// Tag parsing logic omitted for brevity
	return header, nil
}
