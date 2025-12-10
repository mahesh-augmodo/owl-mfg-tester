package fonts

import (
	_ "embed"
)

//go:embed NotoSansSC-VariableFont_wght.ttf
var ChineseFont []byte

//go:embed BitcountPropSingle-VariableFont_CRSV,ELSH,ELXP,slnt,wght.ttf
var EnglishFont []byte
