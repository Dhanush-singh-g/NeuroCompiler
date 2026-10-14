window.NEURO_RESULTS = {
  "schema_version": 1,
  "exported_at": "2026-10-13T13:56:08.299280+00:00",
  "study": "expanded_20261012",
  "recorded_at": "2026-10-12T14:50:38.006978+00:00",
  "context": {
    "cpu_model": "INTEL(R) XEON(R) PLATINUM 8573C",
    "kernel": "6.18.44",
    "cpu_quota": "400000 100000"
  },
  "settings": [
    "O3",
    "O2",
    "O3_no_vector",
    "O3_large_inline"
  ],
  "active_choices": [
    "O3",
    "O2",
    "O3_no_vector"
  ],
  "corpus": {
    "status": "complete",
    "training_programs": 21,
    "training_inputs": 42,
    "correctness_cells": 168,
    "development_programs": 2
  },
  "programs": [
    {
      "id": "sha256",
      "name": "B-Con SHA256",
      "category": "Cryptography",
      "split": "training",
      "inputs": [
        {
          "id": "sha256_pattern",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "8449788570ef030c27a2b8f68d63bf67fa64e375d65aa86a4d4e19096779e99d"
        },
        {
          "id": "sha256_random",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "562fe617cce104551062573597c1cc57abc6d00e95b6b5ac0c9585defb59d022"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "525d7b38eb549e52b21f6fc5e21362b912d66912aa458a5e4819f9427fc8f477",
        "url": "https://codeload.github.com/B-Con/crypto-algorithms/tar.gz/cfbde48414baacf51fc7c74f275190881f037d32"
      }
    },
    {
      "id": "blake2",
      "name": "BLAKE2",
      "category": "Cryptography",
      "split": "training",
      "inputs": [
        {
          "id": "blake2_pattern",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "92ff30cbc2651093329309340beae22572e7d5223a001f2ffc4d31aa164d92f9"
        },
        {
          "id": "blake2_random",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "5781f2e74e559d04398c0fd03eec13fb6ebcf636fd2d4b3074a1b291accca1a2"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "7f2c72859d462d604ab3c9b568c03e97b50a4052092205ad18733d254070ddc2",
        "url": "https://codeload.github.com/BLAKE2/BLAKE2/tar.gz/refs/tags/20190724"
      }
    },
    {
      "id": "bzip2",
      "name": "BZip2",
      "category": "Compression",
      "split": "training",
      "inputs": [
        {
          "id": "bzip2_pattern",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "f1069a06e7a9566831c9ca40872c5bba28ffee4e0edfa8d017a7e621bd75f8ca"
        },
        {
          "id": "bzip2_random",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "3851310634c5122322578c649b5954a3f33b12bdae403b99b3ca00bed73146a9"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "ab5a03176ee106d3f0fa90e381da478ddae405918153cca248e682cd0c4a2269",
        "url": "https://sourceware.org/pub/bzip2/bzip2-1.0.8.tar.gz"
      }
    },
    {
      "id": "cjson",
      "name": "cJSON",
      "category": "JSON / serialization",
      "split": "training",
      "inputs": [
        {
          "id": "cjson_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "2d05d80061a4bc6decec470553e86ba518d904c39a563451ae6bf022d3eb457f"
        },
        {
          "id": "cjson_nested",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "aad9c698bf8c678bdbfd43b2ef8d71b7da8b691789f6fce81761b449c9234ba7"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "7fa616e3046edfa7a28a32d5f9eacfd23f92900fe1f8ccd988c1662f30454562",
        "url": "https://codeload.github.com/DaveGamble/cJSON/tar.gz/refs/tags/v1.7.19"
      }
    },
    {
      "id": "expat",
      "name": "Expat",
      "category": "Parsing",
      "split": "training",
      "inputs": [
        {
          "id": "expat_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "450f9c77b468ad759d802aae713ccee2b4de9488918da955fb5c76ac27182e87"
        },
        {
          "id": "expat_nested",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "b3b44063dd2d6bd6b568841ed7d29953afa45c2641e85a9abb3c9c160aabe375"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "7c853a76f7c2a562c3edfd84ca47e487d9eff3966786191dfb60cc441daf82d6",
        "url": "https://codeload.github.com/libexpat/libexpat/tar.gz/refs/tags/R_2_7_3"
      }
    },
    {
      "id": "fastlz",
      "name": "FastLZ",
      "category": "Compression",
      "split": "training",
      "inputs": [
        {
          "id": "fastlz_pattern",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "1a737fc3c829aa32a80806c7352710f4a9bfc5ea5ec8ac686ad295088c735a0f"
        },
        {
          "id": "fastlz_random",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "ec77b375cf0b52c3a4ac3e794558f16e02c1d6ec21ea8d356a2fe3849f79f542"
        }
      ],
      "pin": {
        "repository": "ariya/FastLZ",
        "commit": "b1342dabcf5257ab303743c9332fe75e9147a011",
        "sha256": "655f998deef53f4924ce8282a3b875ab43ee31189c3c04efdd7c9d73811d7324",
        "url": "https://codeload.github.com/ariya/FastLZ/tar.gz/b1342dabcf5257ab303743c9332fe75e9147a011"
      }
    },
    {
      "id": "frozen",
      "name": "Frozen",
      "category": "JSON / serialization",
      "split": "training",
      "inputs": [
        {
          "id": "frozen_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "2d05d80061a4bc6decec470553e86ba518d904c39a563451ae6bf022d3eb457f"
        },
        {
          "id": "frozen_nested",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "aad9c698bf8c678bdbfd43b2ef8d71b7da8b691789f6fce81761b449c9234ba7"
        }
      ],
      "pin": {
        "repository": "cesanta/frozen",
        "commit": "a42fc3365d7d4e96a5be146b88870dabc794bbc8",
        "sha256": "fb3966b2cc12331807d67d813b32048ccd64d993b48adbee745ec4d8e3a9d884",
        "url": "https://codeload.github.com/cesanta/frozen/tar.gz/a42fc3365d7d4e96a5be146b88870dabc794bbc8"
      }
    },
    {
      "id": "inih",
      "name": "inih",
      "category": "Parsing",
      "split": "training",
      "inputs": [
        {
          "id": "inih_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "39e0b122493a4846d9de836d07aa438b1862be48a10c73c205641be2b06542ce"
        },
        {
          "id": "inih_sections",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "214f5d8c0e05f0a7a7a890033b96f56b499e30c06df13cb49d00ff6f5d2601b4"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "9c15fa751bb8093d042dae1b9f125eb45198c32c6704cd5481ccde460d4f8151",
        "url": "https://codeload.github.com/benhoyt/inih/tar.gz/refs/tags/r62"
      }
    },
    {
      "id": "jsmn",
      "name": "jsmn",
      "category": "JSON / serialization",
      "split": "training",
      "inputs": [
        {
          "id": "jsmn_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "94180f9a03efd5e927d17bec57fb943211fc6c9297aade5ee06abdfa62fbd7a1"
        },
        {
          "id": "jsmn_nested",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "e40bd67ccba12627fd1e513fa0c1414619cc7cf52f4b8656ba89ab0271cc039b"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "5f0913a10657fe7ec8d5794ccf00a01000e3e1f2f1e1f143c34a0f7b47edcb38",
        "url": "https://codeload.github.com/zserge/jsmn/tar.gz/refs/tags/v1.1.0"
      }
    },
    {
      "id": "jsonparser",
      "name": "json-parser",
      "category": "JSON / serialization",
      "split": "training",
      "inputs": [
        {
          "id": "jsonparser_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "2d05d80061a4bc6decec470553e86ba518d904c39a563451ae6bf022d3eb457f"
        },
        {
          "id": "jsonparser_nested",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "aad9c698bf8c678bdbfd43b2ef8d71b7da8b691789f6fce81761b449c9234ba7"
        }
      ],
      "pin": {
        "repository": "udp/json-parser",
        "commit": "9d50ae5ea2cdeef3b75146c621ec7b26e2e3642f",
        "sha256": "dec037375479118305d3f28aa943aa4b47ab2b4b35aeae26faf2c57bf29c0bb9",
        "url": "https://codeload.github.com/udp/json-parser/tar.gz/9d50ae5ea2cdeef3b75146c621ec7b26e2e3642f"
      }
    },
    {
      "id": "lua",
      "name": "Lua",
      "category": "Interpreter",
      "split": "training",
      "inputs": [
        {
          "id": "lua_numeric",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "80efa4e8c04f15e926a5f56e5aa803c25d0677ef40538eec09dad1a4d1b5b34f"
        },
        {
          "id": "lua_tables",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "3817fa58f9acf39f641c93e8339e36c4ae03499f08967c7a1424ff463543977d"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "4f18ddae154e793e46eeab727c59ef1c0c0c2b744e7b94219710d76f530629ae",
        "url": "https://www.lua.org/ftp/lua-5.4.8.tar.gz"
      }
    },
    {
      "id": "lz4",
      "name": "LZ4",
      "category": "Compression",
      "split": "training",
      "inputs": [
        {
          "id": "lz4_pattern",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "1a737fc3c829aa32a80806c7352710f4a9bfc5ea5ec8ac686ad295088c735a0f"
        },
        {
          "id": "lz4_random",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "ec77b375cf0b52c3a4ac3e794558f16e02c1d6ec21ea8d356a2fe3849f79f542"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "537512904744b35e232912055ccf8ec66d768639ff3abe5788d90d792ec5f48b",
        "url": "https://codeload.github.com/lz4/lz4/tar.gz/refs/tags/v1.10.0"
      }
    },
    {
      "id": "miniz",
      "name": "miniz",
      "category": "Compression",
      "split": "training",
      "inputs": [
        {
          "id": "miniz_pattern",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "1a737fc3c829aa32a80806c7352710f4a9bfc5ea5ec8ac686ad295088c735a0f"
        },
        {
          "id": "miniz_random",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "ec77b375cf0b52c3a4ac3e794558f16e02c1d6ec21ea8d356a2fe3849f79f542"
        }
      ],
      "pin": {
        "repository": "richgel999/miniz",
        "commit": "2948eebafc5b9f1c69bebed80333e403a09bd62d",
        "sha256": "3f8dff991d25d7ba1d1247f897c448a59624faed4969541c98a850e23344d998",
        "url": "https://codeload.github.com/richgel999/miniz/tar.gz/2948eebafc5b9f1c69bebed80333e403a09bd62d"
      }
    },
    {
      "id": "monocypher",
      "name": "Monocypher",
      "category": "Cryptography",
      "split": "training",
      "inputs": [
        {
          "id": "monocypher_pattern",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "8449788570ef030c27a2b8f68d63bf67fa64e375d65aa86a4d4e19096779e99d"
        },
        {
          "id": "monocypher_random",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "562fe617cce104551062573597c1cc57abc6d00e95b6b5ac0c9585defb59d022"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "bc1ca30b1b2654e4e7daf2492c0d204200e55137f23fda6b7142fd7d523bd6b4",
        "url": "https://codeload.github.com/LoupVaillant/Monocypher/tar.gz/refs/tags/4.0.2"
      }
    },
    {
      "id": "mpack",
      "name": "MPack",
      "category": "JSON / serialization",
      "split": "training",
      "inputs": [
        {
          "id": "mpack_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "95835f9352001f7dc0e679ad5ccf7f2d3ccdc421d6354e43e97db87f533256dd"
        },
        {
          "id": "mpack_nested",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "1c9e238e68208f0e0f8db15c1905f4ab2344ccc2443ba1a26cebbe9ed1786493"
        }
      ],
      "pin": {
        "repository": "ludocode/mpack",
        "commit": "c9d1820ecfdbc3954c60a218492251e457cc1f86",
        "sha256": "11eb1c7d6b364d9ac03cf4ade407575d008a16a7017e4c3d65d847a63f0df2a7",
        "url": "https://codeload.github.com/ludocode/mpack/tar.gz/c9d1820ecfdbc3954c60a218492251e457cc1f86"
      }
    },
    {
      "id": "parson",
      "name": "Parson",
      "category": "JSON / serialization",
      "split": "training",
      "inputs": [
        {
          "id": "parson_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "2d05d80061a4bc6decec470553e86ba518d904c39a563451ae6bf022d3eb457f"
        },
        {
          "id": "parson_nested",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "aad9c698bf8c678bdbfd43b2ef8d71b7da8b691789f6fce81761b449c9234ba7"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "9ca55b19539a019dd86234543a965be4533be600a8d2539d0046322888df4a41",
        "url": "https://codeload.github.com/kgabis/parson/tar.gz/ec53fb6528b45811df9db0db22cab96a94a96a11"
      }
    },
    {
      "id": "picohttp",
      "name": "picohttpparser",
      "category": "Parsing",
      "split": "training",
      "inputs": [
        {
          "id": "picohttp_short",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "ac2ccd59fd833502d5a4093f65c8cc9bf9e4efdba300b22d821709721af4f822"
        },
        {
          "id": "picohttp_headers",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "9a92f1bb9226433fb637727ff58f7430c072eed5b23833be5cd8437557543b6d"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "d65d80b362fcb11f6e982ebc4515442d93b937b166558120031c38a8b6c173cd",
        "url": "https://codeload.github.com/h2o/picohttpparser/tar.gz/465a7ff09fbd3432fe56c673451f5460154d1f07"
      }
    },
    {
      "id": "tinyexpr",
      "name": "TinyExpr",
      "category": "Interpreter",
      "split": "training",
      "inputs": [
        {
          "id": "tinyexpr_arithmetic",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "a16b8f5e425f36025c43f49fea827c26675efb54f923eeb414be89f89b58f064"
        },
        {
          "id": "tinyexpr_functions",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "ad6f5cfea1562aa801007ad2e44924bdc4e26aa5ff1d3dee9804e71ca058b150"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "0eca2972395bfd49910f72993a990640540838776cc9bbcdbfc130d81a87c7d5",
        "url": "https://codeload.github.com/codeplea/tinyexpr/tar.gz/refs/tags/v1.1.1"
      }
    },
    {
      "id": "yxml",
      "name": "yxml",
      "category": "Parsing",
      "split": "training",
      "inputs": [
        {
          "id": "yxml_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "85d0705915fdb6653b11c3e35c24a8f0f8f33f360c30cb790dd4ecbbeb3de9fb"
        },
        {
          "id": "yxml_nested",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "74617c9e38b59d1146e45f7db01ba7fa579668016c14cdc2114f9972637161b9"
        }
      ],
      "pin": {
        "repository": "JulStrat/yxml",
        "commit": "cb1c99c7271a06687a6d945066533504b396652f",
        "sha256": "ca3bc60a254dff9f403b97ffc204707bb3fdc4cec4456aa5055327840434dffc",
        "url": "https://codeload.github.com/JulStrat/yxml/tar.gz/cb1c99c7271a06687a6d945066533504b396652f"
      }
    },
    {
      "id": "yyjson",
      "name": "yyjson",
      "category": "JSON / serialization",
      "split": "training",
      "inputs": [
        {
          "id": "yyjson_flat",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "2d05d80061a4bc6decec470553e86ba518d904c39a563451ae6bf022d3eb457f"
        },
        {
          "id": "yyjson_nested",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "aad9c698bf8c678bdbfd43b2ef8d71b7da8b691789f6fce81761b449c9234ba7"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "0d901cb2c45c5586e3f3a4245e58c2252d6b24bf4b402723f6179523d389b165",
        "url": "https://codeload.github.com/ibireme/yyjson/tar.gz/refs/tags/0.10.0"
      }
    },
    {
      "id": "zlib",
      "name": "zlib",
      "category": "Compression",
      "split": "training",
      "inputs": [
        {
          "id": "zlib_pattern",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "1a737fc3c829aa32a80806c7352710f4a9bfc5ea5ec8ac686ad295088c735a0f"
        },
        {
          "id": "zlib_random",
          "settings": {
            "O3": "passed",
            "O2": "passed",
            "O3_no_vector": "passed",
            "O3_large_inline": "passed"
          },
          "eligible": true,
          "feature_count": 95,
          "input_sha256": "ec77b375cf0b52c3a4ac3e794558f16e02c1d6ec21ea8d356a2fe3849f79f542"
        }
      ],
      "pin": {
        "repository": null,
        "commit": null,
        "sha256": "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23",
        "url": "https://zlib.net/fossils/zlib-1.3.1.tar.gz"
      }
    },
    {
      "id": "jsonh",
      "name": "json.h",
      "category": "JSON / serialization",
      "split": "development",
      "inputs": [
        {
          "id": "jsonh_flat",
          "settings": {
            "O3": "unrun",
            "O2": "unrun",
            "O3_no_vector": "unrun",
            "O3_large_inline": "unrun"
          },
          "eligible": null,
          "feature_count": null,
          "input_sha256": null
        },
        {
          "id": "jsonh_nested",
          "settings": {
            "O3": "unrun",
            "O2": "unrun",
            "O3_no_vector": "unrun",
            "O3_large_inline": "unrun"
          },
          "eligible": null,
          "feature_count": null,
          "input_sha256": null
        }
      ],
      "pin": {
        "repository": "sheredom/json.h",
        "commit": "079e22385c1b98cb0a9fc733c19e4023eaa4e2b8",
        "sha256": "e2df7b5e462c57d5e6d728c1cb96b8d41f4059abc0c73f138047466488ab3916",
        "url": "https://codeload.github.com/sheredom/json.h/tar.gz/079e22385c1b98cb0a9fc733c19e4023eaa4e2b8"
      }
    },
    {
      "id": "libdeflate",
      "name": "libdeflate",
      "category": "Compression",
      "split": "development",
      "inputs": [
        {
          "id": "libdeflate_pattern",
          "settings": {
            "O3": "unrun",
            "O2": "unrun",
            "O3_no_vector": "unrun",
            "O3_large_inline": "unrun"
          },
          "eligible": null,
          "feature_count": null,
          "input_sha256": null
        },
        {
          "id": "libdeflate_random",
          "settings": {
            "O3": "unrun",
            "O2": "unrun",
            "O3_no_vector": "unrun",
            "O3_large_inline": "unrun"
          },
          "eligible": null,
          "feature_count": null,
          "input_sha256": null
        }
      ],
      "pin": {
        "repository": "ebiggers/libdeflate",
        "commit": "92e6a0db9fa848d742f9eb286c92afc60f2c3dda",
        "sha256": "af56498149827f5a5e3f1ffb653c79c8c75557f3dc2caf6002cac38a59b844b7",
        "url": "https://codeload.github.com/ebiggers/libdeflate/tar.gz/92e6a0db9fa848d742f9eb286c92afc60f2c3dda"
      }
    }
  ],
  "measurement": {
    "status": "failed",
    "targets": [
      {
        "cpu": 0,
        "counts": {
          "cpu": 3,
          "wall": 3
        },
        "total": 6,
        "statistics": {
          "zlib_random": {
            "cpu": {
              "ratio": 0.9994141282450613,
              "interval": [
                0.9567702203108073,
                1.1131128338013547
              ],
              "blocks": [
                1.0597734095730635,
                0.9775294187287665,
                0.9994141282450613
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 0.9998884447990996,
              "interval": [
                0.9567067883889434,
                1.1130688419415584
              ],
              "blocks": [
                1.059740736959119,
                0.9775006797783063,
                0.9998884447990996
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            }
          },
          "expat_nested": {
            "cpu": {
              "ratio": 0.9850914181009839,
              "interval": [
                0.9731692813604467,
                1.0054677168392707
              ],
              "blocks": [
                0.9850914181009839,
                0.9827706524233021,
                1.0002882459130513
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 0.9848762948689536,
              "interval": [
                0.9730873159530479,
                1.005705423652525
              ],
              "blocks": [
                0.9848762948689536,
                0.9824444547199576,
                0.9981674690901591
              ],
              "passed": true,
              "reasons": []
            }
          },
          "lz4_random": {
            "cpu": {
              "ratio": 0.9970607200762595,
              "interval": [
                0.9827657572786467,
                1.0305991346145502
              ],
              "blocks": [
                0.9926062012473162,
                0.9970607200762595,
                1.0099136567670277
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 0.999907456069068,
              "interval": [
                0.9829912947934677,
                1.0306697935810234
              ],
              "blocks": [
                0.9925695608214218,
                0.999907456069068,
                1.0098762648791848
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Interval outside tolerance"
              ]
            }
          },
          "jsonparser_nested": {
            "cpu": {
              "ratio": 0.9888460023206379,
              "interval": [
                0.9752563654228491,
                1.006919188686679
              ],
              "blocks": [
                0.9901052892095354,
                0.9836089814748042,
                0.9888460023206379
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 0.9872468234123213,
              "interval": [
                0.9747771921296958,
                1.0075255201083169
              ],
              "blocks": [
                0.9902086092696599,
                0.9834528120553239,
                0.9872468234123213
              ],
              "passed": true,
              "reasons": []
            }
          },
          "miniz_random": {
            "cpu": {
              "ratio": 0.9405925131661792,
              "interval": [
                0.8847271327145122,
                1.0871059281937718
              ],
              "blocks": [
                0.9348075048527549,
                0.9405925131661792,
                1.0431900093074078
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 0.9406021604544699,
              "interval": [
                0.8847403041314716,
                1.0871712830016345
              ],
              "blocks": [
                0.9346947922410137,
                0.9406021604544699,
                1.0431800180925932
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            }
          },
          "mpack_nested": {
            "cpu": {
              "ratio": 1.0098742599107808,
              "interval": [
                0.9790046808444995,
                1.0255727384730058
              ],
              "blocks": [
                0.9801147235162746,
                1.0098742599107808,
                1.010152898397893
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 1.0090398075698426,
              "interval": [
                0.974063019557795,
                1.0250863438472773
              ],
              "blocks": [
                0.9810029895430977,
                1.0099706203430796,
                1.0090398075698426
              ],
              "passed": true,
              "reasons": []
            }
          }
        },
        "admitted": false,
        "source": "results/expanded_cpu0_screen.json",
        "cells": 18,
        "pairs": 432
      },
      {
        "cpu": 1,
        "counts": {
          "cpu": 5,
          "wall": 5
        },
        "total": 6,
        "statistics": {
          "zlib_random": {
            "cpu": {
              "ratio": 0.9982974294819933,
              "interval": [
                0.9909820150654487,
                1.0398464142395047
              ],
              "blocks": [
                1.0235302913029196,
                0.9982974294819933,
                0.9945109761094887
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 0.998294233153982,
              "interval": [
                0.9909323876382706,
                1.039848232451039
              ],
              "blocks": [
                1.0233397114625777,
                0.998294233153982,
                0.9944956601789522
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Interval outside tolerance"
              ]
            }
          },
          "expat_nested": {
            "cpu": {
              "ratio": 1.0010529672557944,
              "interval": [
                0.9970720373351301,
                1.0117033506550734
              ],
              "blocks": [
                1.0084654319385327,
                0.9997869055166806,
                1.0010529672557944
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 1.0010173307985721,
              "interval": [
                0.9970137565477333,
                1.0119806484641483
              ],
              "blocks": [
                1.0083547704496314,
                0.9998683599178773,
                1.0010173307985721
              ],
              "passed": true,
              "reasons": []
            }
          },
          "lz4_random": {
            "cpu": {
              "ratio": 0.9994890198423988,
              "interval": [
                0.9913488827948762,
                1.0084224611489525
              ],
              "blocks": [
                1.0042571567167784,
                0.9944586645915928,
                0.9994890198423988
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 0.9994461854337465,
              "interval": [
                0.9912168789576463,
                1.0083941606831828
              ],
              "blocks": [
                1.0042519794479003,
                0.9943223715983486,
                0.9994461854337465
              ],
              "passed": true,
              "reasons": []
            }
          },
          "jsonparser_nested": {
            "cpu": {
              "ratio": 1.0113947012936308,
              "interval": [
                0.9901915610897385,
                1.0174543147957262
              ],
              "blocks": [
                1.0113947012936308,
                0.9940711729696147,
                1.016122143197767
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 1.011480635751163,
              "interval": [
                0.990272609633045,
                1.01744019889127
              ],
              "blocks": [
                1.011480635751163,
                0.9940943251245219,
                1.016097261859005
              ],
              "passed": true,
              "reasons": []
            }
          },
          "miniz_random": {
            "cpu": {
              "ratio": 0.9986430454461307,
              "interval": [
                0.9924950420103988,
                1.0093932263081027
              ],
              "blocks": [
                0.9966071139318939,
                1.0054152154818532,
                0.9986430454461307
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 0.9986476444557107,
              "interval": [
                0.9936047197957999,
                1.0106558766042382
              ],
              "blocks": [
                0.9984034059972317,
                1.005867435722489,
                0.9986476444557107
              ],
              "passed": true,
              "reasons": []
            }
          },
          "mpack_nested": {
            "cpu": {
              "ratio": 1.0009711374543453,
              "interval": [
                0.996053812531456,
                1.0190044503493338
              ],
              "blocks": [
                1.017250981566632,
                1.0009711374543453,
                1.0006331751311612
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 1.0009578143301572,
              "interval": [
                0.995651228028272,
                1.0193228826284613
              ],
              "blocks": [
                1.0171928750967194,
                1.0009578143301572,
                0.9998507710464511
              ],
              "passed": true,
              "reasons": []
            }
          }
        },
        "admitted": false,
        "source": "results/expanded_target_screen.json",
        "cells": 18,
        "pairs": 432
      },
      {
        "cpu": 2,
        "counts": {
          "cpu": 4,
          "wall": 4
        },
        "total": 6,
        "statistics": {
          "zlib_random": {
            "cpu": {
              "ratio": 1.0053924020865954,
              "interval": [
                0.9951997670848723,
                1.0260828670179534
              ],
              "blocks": [
                1.0198136775338236,
                1.0053924020865954,
                1.004222098094649
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias"
              ]
            },
            "wall": {
              "ratio": 1.00580952949206,
              "interval": [
                0.9969179520954835,
                1.026036277860962
              ],
              "blocks": [
                1.0198047589321408,
                1.00580952949206,
                1.0050115721082695
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias"
              ]
            }
          },
          "expat_nested": {
            "cpu": {
              "ratio": 0.9849317742868196,
              "interval": [
                0.8997894472332474,
                1.0013142717034451
              ],
              "blocks": [
                0.9849317742868196,
                0.9983329596071724,
                0.901414351957711
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 0.9850121081710238,
              "interval": [
                0.8998048637386952,
                1.0012356236412572
              ],
              "blocks": [
                0.9850121081710238,
                0.9983635380556017,
                0.9013522083241634
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            }
          },
          "lz4_random": {
            "cpu": {
              "ratio": 0.9972857631531034,
              "interval": [
                0.9919797749459237,
                1.0081597930030686
              ],
              "blocks": [
                1.0059213176021207,
                0.9972857631531034,
                0.9963091657105453
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 0.9972955611097948,
              "interval": [
                0.9925363916728915,
                1.0101503646096572
              ],
              "blocks": [
                1.0057933511494555,
                0.9972955611097948,
                0.9964085651692408
              ],
              "passed": true,
              "reasons": []
            }
          },
          "jsonparser_nested": {
            "cpu": {
              "ratio": 1.0061669315802555,
              "interval": [
                0.9946645407790636,
                1.0159258552191566
              ],
              "blocks": [
                1.009791022334245,
                0.9976057944299694,
                1.0061669315802555
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 1.006177267859304,
              "interval": [
                0.9941964771438149,
                1.0159309881778535
              ],
              "blocks": [
                1.00989999722807,
                0.9966946129248533,
                1.006177267859304
              ],
              "passed": true,
              "reasons": []
            }
          },
          "miniz_random": {
            "cpu": {
              "ratio": 0.9936174622914808,
              "interval": [
                0.9738154798873264,
                1.0272780901455578
              ],
              "blocks": [
                1.0245247857416497,
                0.9848174113640088,
                0.9936174622914808
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 0.9936078424856256,
              "interval": [
                0.9725259294904081,
                1.0277367767489103
              ],
              "blocks": [
                1.0251507293845037,
                0.9847688117220216,
                0.9936078424856256
              ],
              "passed": true,
              "reasons": []
            }
          },
          "mpack_nested": {
            "cpu": {
              "ratio": 0.995077999614632,
              "interval": [
                0.9836929684543085,
                1.004896295902587
              ],
              "blocks": [
                0.9963961003195818,
                0.995077999614632,
                0.9947775377651089
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 0.994782546274466,
              "interval": [
                0.9825117432471675,
                1.0061848184144697
              ],
              "blocks": [
                0.9963704092200704,
                0.994782546274466,
                0.993776562315518
              ],
              "passed": true,
              "reasons": []
            }
          }
        },
        "admitted": false,
        "source": "results/expanded_native_20261012/gate.json",
        "cells": 18,
        "pairs": 432
      },
      {
        "cpu": 3,
        "counts": {
          "cpu": 3,
          "wall": 2
        },
        "total": 6,
        "statistics": {
          "zlib_random": {
            "cpu": {
              "ratio": 0.9987262942402297,
              "interval": [
                0.951218882228913,
                1.0241686254260767
              ],
              "blocks": [
                1.0126377537098827,
                0.9631482271112557,
                0.9987262942402297
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 0.9984350042201994,
              "interval": [
                0.951392232374414,
                1.0248581960718004
              ],
              "blocks": [
                1.0126217218901377,
                0.964798559758535,
                0.9984350042201994
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            }
          },
          "expat_nested": {
            "cpu": {
              "ratio": 1.0012300512892565,
              "interval": [
                0.9977217593480606,
                1.0212899297042506
              ],
              "blocks": [
                0.9999222401124115,
                1.0152082315812707,
                1.0012300512892565
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 1.0013157781117243,
              "interval": [
                0.9977381658449089,
                1.021302610618635
              ],
              "blocks": [
                0.9999952558613399,
                1.0151361160637804,
                1.0013157781117243
              ],
              "passed": true,
              "reasons": []
            }
          },
          "lz4_random": {
            "cpu": {
              "ratio": 1.0018131812521838,
              "interval": [
                0.9858481740043279,
                1.013309689690433
              ],
              "blocks": [
                0.9926216426141805,
                1.0069365261151566,
                1.0018131812521838
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 1.0018186106789,
              "interval": [
                0.9874275512897258,
                1.0134645680728869
              ],
              "blocks": [
                0.9924348980592864,
                1.004484987984707,
                1.0018186106789
              ],
              "passed": true,
              "reasons": []
            }
          },
          "jsonparser_nested": {
            "cpu": {
              "ratio": 0.9977492938812449,
              "interval": [
                0.9636550138165436,
                1.0105458362123334
              ],
              "blocks": [
                1.0073119756030073,
                0.9709916230152495,
                0.9977492938812449
              ],
              "passed": false,
              "reasons": [
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 0.9977485236471436,
              "interval": [
                0.9635260177105688,
                1.0146013874384539
              ],
              "blocks": [
                1.0072640891644202,
                0.970957721893628,
                0.9977485236471436
              ],
              "passed": false,
              "reasons": [
                "Interval outside tolerance"
              ]
            }
          },
          "miniz_random": {
            "cpu": {
              "ratio": 0.9985858435691948,
              "interval": [
                0.9505230941319207,
                1.0402319798963875
              ],
              "blocks": [
                0.9931517951929503,
                0.9985858435691948,
                1.0001564200994448
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 0.9985375096888794,
              "interval": [
                0.9389160184905283,
                1.0396578426969312
              ],
              "blocks": [
                0.9687725736989217,
                0.9985375096888794,
                1.000124266646656
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            }
          },
          "mpack_nested": {
            "cpu": {
              "ratio": 1.015627627162769,
              "interval": [
                0.9981422211951466,
                1.0296771746064208
              ],
              "blocks": [
                1.015627627162769,
                1.017460658405424,
                1.0025528112603468
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 1.0153650020286724,
              "interval": [
                1.0001950167989937,
                1.0300118383141865
              ],
              "blocks": [
                1.0153650020286724,
                1.0172759061672045,
                1.0030984219444006
              ],
              "passed": false,
              "reasons": [
                "Interval outside tolerance"
              ]
            }
          }
        },
        "admitted": false,
        "source": "results/expanded_target_screen.json",
        "cells": 18,
        "pairs": 432
      },
      {
        "cpu": 4,
        "counts": {
          "cpu": 1,
          "wall": 1
        },
        "total": 6,
        "statistics": {
          "zlib_random": {
            "cpu": {
              "ratio": 1.0018949425473926,
              "interval": [
                0.9653755486719652,
                1.0906088267369987
              ],
              "blocks": [
                0.9946520081844035,
                1.0561760441085308,
                1.0018949425473926
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 1.002768246312488,
              "interval": [
                0.965339200085739,
                1.090698316341659
              ],
              "blocks": [
                0.9947188110481557,
                1.0561701637713374,
                1.002768246312488
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            }
          },
          "expat_nested": {
            "cpu": {
              "ratio": 1.0045132451964887,
              "interval": [
                0.9947891526969771,
                1.0141912796795958
              ],
              "blocks": [
                1.007756749426458,
                1.0045132451964887,
                1.0001978713359119
              ],
              "passed": true,
              "reasons": []
            },
            "wall": {
              "ratio": 1.0045001546018848,
              "interval": [
                0.9941350459072883,
                1.0142244598045411
              ],
              "blocks": [
                1.0077128617429585,
                1.0045001546018848,
                1.000202710895529
              ],
              "passed": true,
              "reasons": []
            }
          },
          "lz4_random": {
            "cpu": {
              "ratio": 0.9974587065361875,
              "interval": [
                0.9871849111045472,
                1.0129176936050073
              ],
              "blocks": [
                0.9974587065361875,
                0.9951044625306146,
                0.9989033462255343
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias"
              ]
            },
            "wall": {
              "ratio": 0.9986274538261963,
              "interval": [
                0.9877727002636285,
                1.010405969554186
              ],
              "blocks": [
                1.0007205702075066,
                0.9951064525723715,
                0.9986274538261963
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias"
              ]
            }
          },
          "jsonparser_nested": {
            "cpu": {
              "ratio": 1.005751924266613,
              "interval": [
                0.9590558728424302,
                1.0113437101338734
              ],
              "blocks": [
                1.0076101576407936,
                0.9704280096349606,
                1.005751924266613
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 1.0057641647448425,
              "interval": [
                0.9592726133407582,
                1.0115129799934135
              ],
              "blocks": [
                1.0076332643141723,
                0.9703752947311193,
                1.0057641647448425
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Block outside tolerance",
                "Interval outside tolerance"
              ]
            }
          },
          "miniz_random": {
            "cpu": {
              "ratio": 0.9996482836632141,
              "interval": [
                0.9762680633129918,
                1.035749447405568
              ],
              "blocks": [
                1.0165557158830383,
                0.9864507457549091,
                0.9996482836632141
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Interval outside tolerance"
              ]
            },
            "wall": {
              "ratio": 0.9999369921723384,
              "interval": [
                0.9762463200125748,
                1.035764902324827
              ],
              "blocks": [
                1.0165747506148815,
                0.986481246875988,
                0.9999369921723384
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias",
                "Interval outside tolerance"
              ]
            }
          },
          "mpack_nested": {
            "cpu": {
              "ratio": 0.9985265951917144,
              "interval": [
                0.9875792302378688,
                1.0075133437703718
              ],
              "blocks": [
                1.0048187075571358,
                0.9921592114020451,
                0.9985265951917144
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias"
              ]
            },
            "wall": {
              "ratio": 0.9983774480291697,
              "interval": [
                0.9870303735878656,
                1.008419854926999
              ],
              "blocks": [
                1.0069331315554342,
                0.9921084632699672,
                0.9983774480291697
              ],
              "passed": false,
              "reasons": [
                "Starting-order bias"
              ]
            }
          }
        },
        "admitted": false,
        "source": "results/expanded_target_screen.json",
        "cells": 18,
        "pairs": 432
      }
    ],
    "cases": [
      "zlib_random",
      "expat_nested",
      "lz4_random",
      "jsonparser_nested",
      "miniz_random",
      "mpack_nested"
    ],
    "cells": 90,
    "pairs": 2160,
    "tolerance": 0.03,
    "source": "results/expanded_native_20261012/frozen.json"
  },
  "model": {
    "status": "not_qualified",
    "default": "O3",
    "qualified_targets": 11,
    "configurations": 16,
    "study": "persistent_20261011",
    "source": "results/persistent_native_20261011_selection.json"
  },
  "headroom": {
    "cpu": {
      "speedup": 1.137116089839001,
      "interval": [
        1.127040056373318,
        1.1450323815728471
      ],
      "blocks": [
        1.1301010249570198,
        1.1433169994985508,
        1.137116089839001
      ]
    },
    "wall": {
      "speedup": 1.137154758297244,
      "interval": [
        1.1269846112680604,
        1.145084133071946
      ],
      "blocks": [
        1.1300681189081747,
        1.1426861203130614,
        1.137154758297244
      ]
    },
    "case": "blake2_random",
    "setting": "O3_no_vector",
    "cpu_time_reduction": 12.058231438657641,
    "source": "results/persistent_probe.json",
    "scope": "Training-only headroom; excluded from model fitting"
  },
  "warnings": [],
  "sources": [
    {
      "path": "results/expanded_native_20261012/frozen.json",
      "status": "loaded",
      "sha256": "40799ed4e29924e664011217d40bcb2265293cd16804e5f96c1d5c811c631a27"
    },
    {
      "path": "results/expanded_native_20261012/preflight.json",
      "status": "loaded",
      "sha256": "ad2182f09ce03d0f30afb4a5613ca1b15da12c5440ee6663cf3f008501cb9154"
    },
    {
      "path": "results/expanded_source_pins.json",
      "status": "loaded",
      "sha256": "70dccf76ab2ce34e19321afd869a934097222c6a1f11ca81b3affd674f381bdc"
    },
    {
      "path": "results/expanded_native_20261012/gate.json",
      "status": "loaded",
      "sha256": "9b51fcb87876d775a642d3fa64a3953f1661190a328ac58e287ec0765c6d4793"
    },
    {
      "path": "results/expanded_target_screen.json",
      "status": "loaded",
      "sha256": "4120259db27d4e491e7646a9f0bb8e716218a957e32a104627995b0ee31923d9"
    },
    {
      "path": "results/expanded_cpu0_screen.json",
      "status": "loaded",
      "sha256": "b7f9b99847809bd4e0f182a0873a8aa9815b30faf207ba6af8f15c12bbc76099"
    },
    {
      "path": "results/persistent_native_20261011_selection.json",
      "status": "loaded",
      "sha256": "c4faf43f7a15cebbaeef02d0b7343bba735116143ecb65ad95c0c7fce746be1d"
    },
    {
      "path": "results/persistent_probe.json",
      "status": "loaded",
      "sha256": "b3402f8e148fe8d7b984240ee24d729fd394a16d280618ae9cc4419c97725548"
    }
  ],
  "reports": [
    "EXPANDED_SL.md",
    "PERSISTENT_SL.md",
    "FINAL_ASSESSMENT.md"
  ]
};
